"""
CycloneX Automatic Alert Monitor — Background Evaluation Loop
Connects the ML prediction pipeline to the alert engine automatically.

Every cycle (default 15 minutes):
1. Reads all active cyclones from the database
2. Runs ML inference for each cyclone to get current predictions
3. Evaluates risk thresholds and triggers alerts when crossed
4. Respects safety interlock, kill switch, deduplication, and escalation
5. Also evaluates the weather grid's most-disturbed point for new developing cyclones

This module closes the critical gap between "ML prediction output" and "alert evaluation input".
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.app.core.config import settings

logger = logging.getLogger("CycloneX.AlertMonitor")


class CycloneAlertMonitor:
    """
    Periodically evaluates all active cyclones against the alert threshold engine
    and dispatches notifications through the full pipeline.
    """

    @classmethod
    def evaluate_active_cyclones(cls, db_session) -> List[Dict[str, Any]]:
        """
        Synchronous evaluation of all active cyclones.
        Returns a list of evaluation results (one per cyclone).
        Can be called directly from API endpoints or background loops.
        """
        from backend.app.models.entities import Cyclone
        from ml.pipeline import ml_pipeline
        from alerts.engine import AlertEngine
        from alerts.notifications.providers import is_kill_switch_active

        results = []

        # Check kill switch first
        if is_kill_switch_active():
            logger.warning("[AlertMonitor] Kill switch is active. Skipping evaluation cycle.")
            return [{"status": "skipped", "reason": "Kill switch active"}]

        # Check monitor enabled
        if not settings.ALERT_MONITOR_ENABLED:
            logger.info("[AlertMonitor] Monitor disabled (ALERT_MONITOR_ENABLED=False). Skipping.")
            return [{"status": "skipped", "reason": "Monitor disabled"}]

        try:
            active_cyclones = db_session.query(Cyclone).filter(
                Cyclone.status.in_(["active", "ACTIVE", "Active"])
            ).all()
        except Exception as e:
            logger.error(f"[AlertMonitor] Failed to query active cyclones: {e}")
            return [{"status": "error", "reason": str(e)}]

        if not active_cyclones:
            logger.info("[AlertMonitor] No active cyclones in database. Evaluation cycle complete.")
            return [{"status": "no_active_cyclones", "evaluated": 0}]

        logger.info(f"[AlertMonitor] Evaluating {len(active_cyclones)} active cyclone(s)...")

        for cyclone in active_cyclones:
            try:
                result = cls._evaluate_single_cyclone(cyclone, ml_pipeline, AlertEngine, db_session)
                results.append(result)
            except Exception as e:
                logger.error(f"[AlertMonitor] Error evaluating cyclone '{cyclone.name}': {e}", exc_info=True)
                results.append({
                    "cyclone_id": cyclone.id,
                    "cyclone_name": cyclone.name,
                    "status": "error",
                    "reason": str(e)
                })

        # Also evaluate the most-disturbed weather grid point for emerging cyclones
        try:
            grid_result = cls._evaluate_weather_grid(AlertEngine, db_session)
            if grid_result:
                results.append(grid_result)
        except Exception as e:
            logger.error(f"[AlertMonitor] Error evaluating weather grid: {e}", exc_info=True)

        triggered_count = sum(1 for r in results if r.get("triggered"))
        suppressed_count = sum(1 for r in results if r.get("action_type") == "DUPLICATE_SUPPRESSED")
        logger.info(
            f"[AlertMonitor] Cycle complete. Evaluated: {len(active_cyclones)} cyclone(s). "
            f"Triggered: {triggered_count}. Suppressed: {suppressed_count}."
        )

        return results

    @classmethod
    def _evaluate_single_cyclone(cls, cyclone, ml_pipeline, AlertEngine, db_session) -> Dict[str, Any]:
        """
        Runs ML inference on a single cyclone and evaluates alert thresholds.
        """
        cyclone_lat = float(cyclone.current_lat or 21.65)
        cyclone_lon = float(cyclone.current_lon or 66.85)
        cyclone_wind = float(cyclone.current_wind_speed_kts or 85.0)
        cyclone_pressure = float(cyclone.current_pressure_hpa or 964.0)
        cyclone_heading = float(cyclone.current_heading_deg or 38.0)
        cyclone_speed = float(cyclone.current_speed_kmh or 11.5)

        # Run ML inference
        inference = ml_pipeline.run_full_inference(
            cyclone_id=cyclone.id,
            current_lat=cyclone_lat,
            current_lon=cyclone_lon,
            current_wind_kts=cyclone_wind,
            current_pressure_hpa=cyclone_pressure,
            current_heading_deg=cyclone_heading,
            current_speed_kmh=cyclone_speed
        )

        # Extract peak predicted wind from forecast points
        forecast_points = inference.get("forecast_points", [])
        if forecast_points:
            peak_wind = max(fp.get("predicted_wind_speed_kts", 0) for fp in forecast_points)
            peak_pressure = min(fp.get("predicted_pressure_hpa", 1013) for fp in forecast_points)
            # Use first forecast point uncertainty for risk calculation
            uncertainty = forecast_points[0].get("uncertainty_radius_km", 60.0)
        else:
            peak_wind = cyclone_wind
            peak_pressure = cyclone_pressure
            uncertainty = 60.0

        # Determine location and affected districts
        target_location = _resolve_target_location(cyclone_lat, cyclone_lon, cyclone.name)
        affected_districts = _resolve_affected_districts(cyclone_lat, cyclone_lon)

        # Estimate ETA based on proximity to coast (~500km assumed for open sea)
        landfall_eta_hours = max(6, int(500.0 / max(cyclone_speed, 5.0)))

        logger.info(
            f"[AlertMonitor] Cyclone '{cyclone.name}' — "
            f"Peak Wind: {peak_wind:.0f} kts, Pressure: {peak_pressure:.0f} hPa, "
            f"ETA: ~{landfall_eta_hours}h, Districts: {', '.join(affected_districts)}"
        )

        # Run the full alert pipeline
        result = AlertEngine.evaluate_and_trigger(
            cyclone_name=cyclone.name,
            predicted_wind_kts=peak_wind,
            central_pressure_hpa=peak_pressure,
            landfall_eta_hours=landfall_eta_hours,
            target_location=target_location,
            affected_districts=affected_districts,
            uncertainty_radius_km=uncertainty,
            cyclone_id=cyclone.id,
            channels=["dashboard", "sms", "email"],
            is_simulation=False,  # Real dispatch — safety switch controls actual delivery
            force_dispatch=False,
            db_session=db_session
        )

        result["cyclone_name"] = cyclone.name
        result["ml_inference_summary"] = {
            "peak_predicted_wind_kts": round(peak_wind, 1),
            "min_predicted_pressure_hpa": round(peak_pressure, 1),
            "uncertainty_radius_km": round(uncertainty, 1),
            "landfall_eta_hours": landfall_eta_hours,
            "detection_status": inference.get("detection", {}).get("status", "Unknown"),
            "model_version": inference.get("model_version", "Unknown")
        }

        if result.get("triggered"):
            logger.info(
                f"[AlertMonitor] *** ALERT TRIGGERED *** for '{cyclone.name}' — "
                f"Level: {result.get('alert_level')}, Risk: {result.get('risk_score', 0):.2f}, "
                f"Dispatches: {result.get('dispatches_count', 0)}"
            )
        else:
            logger.info(
                f"[AlertMonitor] No alert for '{cyclone.name}': {result.get('action_type', 'NO_ALERT')}"
            )

        return result

    @classmethod
    def _evaluate_weather_grid(cls, AlertEngine, db_session) -> Optional[Dict[str, Any]]:
        """
        Evaluates the most-disturbed weather grid point for emerging cyclone signatures.
        Only triggers if the disturbance score is exceptionally high (>=70) and wind > 34 kts.
        """
        from backend.app.core.weather_cache import weather_cache

        most_disturbed = weather_cache.get_most_disturbed()
        if not most_disturbed:
            return None

        point = most_disturbed.get("point", most_disturbed)
        wind_kts = float(point.get("surface_wind_10m_kts", 0))
        pressure = float(point.get("sea_level_pressure_hpa", 1013))
        disturbance_score = float(point.get("disturbance_score", 0))
        station_name = point.get("name", "Unknown Station")

        # Only evaluate if conditions are significantly disturbed
        if disturbance_score < 70.0 or wind_kts < 34.0:
            return None

        logger.info(
            f"[AlertMonitor] Weather grid hotspot detected: {station_name} — "
            f"Wind: {wind_kts:.0f} kts, Pressure: {pressure:.0f} hPa, "
            f"Disturbance: {disturbance_score:.1f}"
        )

        lat = float(point.get("lat", 20.0))
        lon = float(point.get("lon", 70.0))
        target_location = f"{station_name}, {point.get('state', 'Coastal India')}"
        districts = _resolve_affected_districts(lat, lon)

        result = AlertEngine.evaluate_and_trigger(
            cyclone_name=f"DEVELOPING-{station_name.upper().replace(' ', '-')[:12]}",
            predicted_wind_kts=wind_kts,
            central_pressure_hpa=pressure,
            landfall_eta_hours=48,
            target_location=target_location,
            affected_districts=districts,
            uncertainty_radius_km=120.0,
            cyclone_id=f"grid-detect-{point.get('id', 'unknown')}",
            channels=["dashboard"],  # Weather grid alerts go to dashboard only initially
            is_simulation=False,
            force_dispatch=False,
            db_session=db_session
        )

        result["source"] = "WEATHER_GRID_AUTO_DETECT"
        result["station_name"] = station_name
        return result


def _resolve_target_location(lat: float, lon: float, cyclone_name: str) -> str:
    """Resolves a human-readable location description from coordinates."""
    if 60.0 <= lon <= 72.0 and 15.0 <= lat <= 24.0:
        return f"{cyclone_name} Approach Path — Kutch & Saurashtra Coast, Gujarat"
    elif 72.0 <= lon <= 77.0 and 15.0 <= lat <= 22.0:
        return f"{cyclone_name} Approach Path — South Gujarat & Maharashtra Coast"
    elif 80.0 <= lon <= 88.0 and 15.0 <= lat <= 22.0:
        return f"{cyclone_name} Approach Path — Andhra Pradesh & Odisha Coast"
    elif 86.0 <= lon <= 92.0 and 20.0 <= lat <= 24.0:
        return f"{cyclone_name} Approach Path — West Bengal & Odisha Coast"
    elif 78.0 <= lon <= 82.0 and 8.0 <= lat <= 14.0:
        return f"{cyclone_name} Approach Path — Tamil Nadu Coast"
    else:
        return f"Cyclone {cyclone_name} — North Indian Ocean ({lat:.1f}°N, {lon:.1f}°E)"


def _resolve_affected_districts(lat: float, lon: float) -> List[str]:
    """Resolves likely affected coastal districts based on cyclone coordinates."""
    # Gujarat — Kutch/Saurashtra
    if 60.0 <= lon <= 72.0 and 20.0 <= lat <= 24.5:
        return ["Kutch", "Devbhumi Dwarka", "Jamnagar"]
    elif 72.0 <= lon <= 74.0 and 18.0 <= lat <= 22.0:
        return ["Porbandar", "Morbi", "Jamnagar"]
    # Odisha
    elif 84.0 <= lon <= 88.0 and 18.0 <= lat <= 22.0:
        return ["Puri", "Jagatsinghpur"]
    # Andhra Pradesh
    elif 80.0 <= lon <= 84.0 and 15.0 <= lat <= 18.0:
        return ["Visakhapatnam"]
    # West Bengal
    elif 86.0 <= lon <= 90.0 and 20.0 <= lat <= 24.0:
        return ["South 24 Parganas"]
    # Tamil Nadu
    elif 78.0 <= lon <= 82.0 and 8.0 <= lat <= 14.0:
        return ["Nagapattinam"]
    else:
        return ["Kutch", "Devbhumi Dwarka"]


async def alert_monitor_loop():
    """
    Async background loop that periodically evaluates active cyclones.
    Runs inside the FastAPI lifespan alongside the Open-Meteo weather poller.
    """
    from backend.app.core.database import SessionLocal

    interval = settings.ALERT_MONITOR_INTERVAL_SECONDS
    logger.info(
        f"[AlertMonitor] Background monitor initialized. "
        f"Interval: {interval}s. Enabled: {settings.ALERT_MONITOR_ENABLED}. "
        f"Live Alerts: {settings.LIVE_ALERTS_ENABLED}."
    )

    # Wait 30 seconds on first startup to let weather cache populate
    try:
        await asyncio.sleep(30)
    except asyncio.CancelledError:
        logger.info("[AlertMonitor] Cancelled during initial startup delay.")
        return

    while True:
        if settings.ALERT_MONITOR_ENABLED:
            db = SessionLocal()
            try:
                results = CycloneAlertMonitor.evaluate_active_cyclones(db)
                triggered = [r for r in results if r.get("triggered")]
                if triggered:
                    logger.info(
                        f"[AlertMonitor] {len(triggered)} alert(s) triggered this cycle."
                    )
            except Exception as exc:
                logger.error(f"[AlertMonitor] Evaluation cycle error: {exc}", exc_info=True)
            finally:
                db.close()
        else:
            logger.debug("[AlertMonitor] Monitor disabled, sleeping.")

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("[AlertMonitor] Background loop cancelled for shutdown.")
            break

