"use client";

import React, { useState } from "react";
import { 
  Search, ChevronDown, ChevronUp, CheckCircle2
} from "lucide-react";

interface QuestionItem {
  id: number;
  category: "ML & Validation" | "Data & Architecture" | "Operational Reality" | "Innovations";
  q: string;
  a: string;
  evidence: string;
}

const QUESTIONS: QuestionItem[] = [
  {
    id: 1,
    category: "Operational Reality",
    q: "What is the problem?",
    a: "Tropical cyclones cause severe coastal destruction and loss of life across the North Indian Ocean basin. Current operational tools often output broad, abstract trajectories and synoptic bulletins without directly bridging the last-mile gap to localized civil defense logistics, infrastructure risk, and real-time evacuation routing for emergency managers.",
    evidence: "Problem statement SIH26070; documented in docs/FINAL_SIH_READINESS.md."
  },
  {
    id: 2,
    category: "Innovations",
    q: "What is novel about CycloneX?",
    a: "Traditional meteorological platforms stop at predicting track and central wind speed. CycloneX closes the entire operational loop: Detect → Classify → Predict → Assess Risk → Explain → Alert → Location Intelligence. We turn abstract trajectories into location-specific, actionable micro-dossiers (distance to eye, local wind proxy, nearest verified shelter, and evacuation corridor) for any clicked geographic coordinate.",
    evidence: "Implemented in backend/app/api/v1/endpoints/cyclones.py and frontend/src/app/dashboard/page.tsx."
  },
  {
    id: 3,
    category: "Data & Architecture",
    q: "What datasets are used?",
    a: "CycloneX ingests across 6 distinct multi-source adapters: (1) NOAA NCEI IBTrACS v04r00 for verified 6-hourly best tracks, (2) NASA GIBS for MODIS Terra/VIIRS reflectance WMTS tiles, (3) Open-Meteo for live NWP wind and pressure, (4) OSM Overpass for verified cyclone shelters and hospitals, (5) OSRM for road corridor distance and driving time, and (6) WorldPop for gridded coastal demographic densities.",
    evidence: "Fully specified in docs/DATA_SOURCES.md with live endpoints and BaseDataAdapter schemas."
  },
  {
    id: 4,
    category: "ML & Validation",
    q: "How is leakage prevented?",
    a: "We conducted a forensic leakage audit eliminating 6 vectors: (1) Storm leakage eliminated via strict Leave-One-Storm-Out cross-validation; (2) Temporal leakage eliminated by ensuring features at time T strictly predict future targets (T+6h); (3) Target leakage eliminated by excluding future wind from classification input; (4) Duplicate leakage eliminated by removing synthetic twin copies; (5) Normalization leakage prevented by avoiding global pre-split scalers; and (6) Artifact leakage prevented by computing validation metrics strictly out-of-fold.",
    evidence: "Documented in docs/ML_REPRODUCIBILITY.md and verified by tests/test_ml_baselines.py."
  },
  {
    id: 5,
    category: "ML & Validation",
    q: "Why LOSO validation?",
    a: "Tropical cyclone observations along a single storm track are highly autocorrelated in time and space. A standard random train_test_split distributes points from the same storm into both train and test sets, allowing the model to memorize storm identity and report artificially inflated metrics (like 1.0 F1). Leave-One-Storm-Out (LOSO) trains on 10 storms and tests on the held-out 11th storm, proving genuine generalization to unseen cyclones.",
    evidence: "Verified across 11 folds in ml/train_baselines.py with zero storm overlap."
  },
  {
    id: 6,
    category: "ML & Validation",
    q: "What are the current metrics?",
    a: "Under strict Leave-One-Storm-Out cross-validation across 247 valid transitions, our Random Forest classifier achieves 67.21% accuracy and 0.6706 weighted F1 across all 6 IMD operational categories (balanced accuracy: 68.80%). For intensity MAE: +6h = 6.32 kt, +12h = 10.21 kt, +24h = 18.40 kt, +48h = 29.96 kt, +72h = 40.70 kt. For track displacement MAE: +6h = 41.3 km, +12h = 75.2 km, +24h = 141.9 km, +48h = 284.6 km, +72h = 388.8 km.",
    evidence: "Logged in ml/artifacts/evaluation_metrics.json and docs/ML_REPRODUCIBILITY.md."
  },
  {
    id: 7,
    category: "ML & Validation",
    q: "Why does classification not beat persistence?",
    a: "Tropical cyclones exhibit high physical inertia over short 6-hour windows, maintaining their discrete operational category in ~70% of consecutive observations. Consequently, naive stage persistence achieves 70.04% at +6h versus 67.21% for CycloneX. However, CycloneX strongly outperforms the majority class baseline (21.46%) and uniform random (16.67%), while beating persistence across all intensity horizons.",
    evidence: "Published transparently on /model-performance and docs/CANONICAL_SIH_METRICS.md."
  },
  {
    id: 8,
    category: "ML & Validation",
    q: "How does intensity prediction work?",
    a: "Intensity prediction uses a gradient boosted regressor (LightGBM) trained on thermodynamic and kinematic predictor vectors, including central pressure deficit, 12-hour pressure tendency, translation velocity, and sea surface temperature proxies. It predicts future sustained wind speed at +6h, +12h, +24h, +48h, and +72h, demonstrating positive skill gain (+14.6% to +32.0%) over persistence across all five horizons.",
    evidence: "Implemented in ml/train_baselines.py and evaluated in tests/test_ml_baselines.py."
  },
  {
    id: 9,
    category: "ML & Validation",
    q: "How does track prediction work?",
    a: "Track forecasting uses forward kinematic extrapolation augmented by historical steering flow vectors. It computes future latitude/longitude displacement over 6h, 12h, 24h, 48h, and 72h lead times using Great-Circle Haversine error benchmarking. While persistence is competitive at short lead times (+6h: 41.3 vs 37.3 km; +12h: 75.2 vs 71.0 km), CycloneX demonstrates positive skill gain at extended horizons (+48h: 284.6 vs 302.1 km, +5.8%; +72h: 388.8 vs 473.5 km, +17.9%).",
    evidence: "Evaluated across 258 observations; exported in artifacts/track_evaluation_predictions.csv."
  },
  {
    id: 10,
    category: "ML & Validation",
    q: "What is the uncertainty cone?",
    a: "The uncertainty cone is an empirical 68% confidence envelope calculated from historical out-of-fold cross-validation position errors. Rather than assuming static circles, the radius expands dynamically with lead time (±35 km at +6h, ±55 km at +12h, ±80 km at +24h, ±115 km at +48h, and ±165 km at +72h), providing decision-makers with a statistically grounded landfall danger zone.",
    evidence: "Calculated in geospatial/risk_engine.py and rendered in MapComponent.tsx."
  },
  {
    id: 11,
    category: "Operational Reality",
    q: "How is population exposure calculated?",
    a: "We query 100m gridded coastal population densities from WorldPop overlaid with the cyclone's gale-force (34-kt) and storm-force (64-kt) wind radii. This isolates the exact coastal blocks and districts with populations within the destructive wind swath.",
    evidence: "Implemented in geospatial/exposure_engine.py and verified in tests/test_geospatial.py."
  },
  {
    id: 12,
    category: "Innovations",
    q: "How does location intelligence work?",
    a: "When an operator clicks any point on the map, the API calculates: (1) Great-circle distance and azimuth bearing to eye; (2) Local wind speed proxy using a modified Holland vortex profile; (3) UNDRR composite risk score; (4) Nearest government cyclone shelter from OSM; (5) Nearest trauma hospital; (6) Navigable evacuation route via OSRM; and (7) Stakeholder-specific actionable checklists.",
    evidence: "Verified across multiple arbitrary coordinates in tests/test_location_intelligence.py."
  },
  {
    id: 13,
    category: "Data & Architecture",
    q: "What happens if an API fails?",
    a: "Every external adapter inherits from BaseDataAdapter with a 5-to-8-second timeout circuit breaker. If an external API (like Open-Meteo or OSM) is unreachable, the system automatically falls back to verified offline catalogs without throwing unhandled exceptions or crashing the UI. The response payload explicitly flags data_status: FALLBACK_DATA.",
    evidence: "Tested in tests/test_data_adapters.py with simulated network timeouts."
  },
  {
    id: 14,
    category: "Operational Reality",
    q: "Does CycloneX replace IMD?",
    a: "No. The India Meteorological Department (IMD) is the statutory national authority for cyclone categorization, official landfall timing, and coastal storm surge warnings in India. CycloneX benchmarks against IMD standards and serves as a rapid decision-support tool for local district magistrates, not a replacement for IMD bulletins.",
    evidence: "Operational disclaimers prominently displayed on /dashboard and in docs/RISK_MODEL.md."
  },
  {
    id: 15,
    category: "ML & Validation",
    q: "Is the satellite deep-learning model trained?",
    a: "No, and we are completely transparent about this. Training an operational deep satellite vision model (CNN or ViT) requires 10⁵+ multi-spectral INSAT-3D/3DR or HIMAWARI NetCDF4 scenes. We have implemented the complete 8-stage image preprocessing pipeline with an analytical spectral-gradient vortex curvature baseline, and established the storm-partitioned dataset structure ready for deep weight ingestion.",
    evidence: "Documented in ml/satellite_detector.py, docs/MODEL_STATUS.md, and labeled as 'NOT TRAINED — DATASET REQUIRED'."
  },
  {
    id: 16,
    category: "Operational Reality",
    q: "How can the system be deployed nationally?",
    a: "For operational deployment, the roadmap requires: (1) Direct automated feeds from ISRO/IMD INSAT-3D/3DR meteorological satellites; (2) Deploying the SQLite database to a high-availability PostGIS cluster on AWS/NIC cloud; (3) Integration with the National Common Alerting Protocol (CAP) for automated cell-broadcast SMS dispatch; and (4) Real-time Doppler Weather Radar (DWR) coastal sweeps.",
    evidence: "Documented in docs/FINAL_SIH_READINESS.md under Production Gaps."
  },
  {
    id: 17,
    category: "Innovations",
    q: "What is the future roadmap?",
    a: "Our future engineering roadmap focuses on: (1) Training a Vision Transformer (ViT) backbone on 100k+ INSAT-3D scenes; (2) Coupling with 2D shallow-water ADCIRC hydrodynamic storm surge models; (3) Multi-modal LLM synthetic report drafting for District Collectors; and (4) Multilingual voice alert dissemination via regional telephony gateways.",
    evidence: "Documented in docs/FINAL_SIH_READINESS.md and data/satellite_dataset.py."
  }
];

export default function JudgeQAPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCat, setSelectedCat] = useState<string>("All");
  const [expandedId, setExpandedId] = useState<number | null>(1);

  const categories = ["All", "ML & Validation", "Operational Reality", "Data & Architecture", "Innovations"];

  const filtered = QUESTIONS.filter((item) => {
    const matchesCat = selectedCat === "All" || item.category === selectedCat;
    const matchesSearch = item.q.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          item.a.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto w-full space-y-6">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded p-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight uppercase font-mono">
              JURY Q&A & TECHNICAL DEFENSE
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              17 Evidence-Based Defenses • Model Validation, Architecture, Preventions & Operational Limits
            </p>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            DEFENSE DOSSIER • SIH26070 AUDIT
          </div>
        </div>
      </div>

      {/* Clean System Architecture & Operational Pipeline */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <span className="text-xs font-semibold text-slate-800 uppercase tracking-wider font-mono">
            System Architecture & Data Pipeline
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
            End-to-End Operational Pipeline
          </span>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-200 rounded font-mono text-xs text-slate-700 overflow-x-auto">
          <div className="flex flex-col space-y-1.5 leading-snug">
            <div className="font-semibold text-slate-900">MULTI-SOURCE DATA INGESTION</div>
            <div className="text-slate-600 pl-3">
              ├── NOAA IBTrACS v04r00 (Verified Best Track Fixes)<br />
              ├── NASA GIBS (MODIS Terra/VIIRS Reflectance WMTS Tiles)<br />
              ├── Open-Meteo (Live NWP Surface Wind, Gusts, Barometric Pressure)<br />
              ├── Ocean Temperature (Sea Surface Temperature Anomalies)<br />
              ├── WorldPop (100m Gridded Coastal Population Censuses)<br />
              └── OpenStreetMap / OSRM (Designated MPCS Shelters & Evacuation Routing)
            </div>
            <div className="text-slate-400 pl-6">↓</div>
            <div className="font-semibold text-slate-900 pl-3">DATA PREPROCESSING & ADAPTER CIRCUIT BREAKERS (5s Timeout Fallback)</div>
            <div className="text-slate-400 pl-6">↓</div>
            <div className="font-semibold text-slate-900 pl-3">CYCLONE DETECTION (Analytical Spectral-Gradient Vorticity Baseline)</div>
            <div className="text-slate-400 pl-6">↓</div>
            <div className="font-semibold text-slate-900 pl-3">STAGE CLASSIFICATION (Random Forest Classifier, 67.21% LOSO Accuracy)</div>
            <div className="text-slate-400 pl-6">↓</div>
            <div className="font-semibold text-slate-900 pl-3">INTENSITY & TRACK FORECASTING (LightGBM Regression across +6h, +12h, +24h, +48h, +72h)</div>
            <div className="text-slate-400 pl-6">↓</div>
            <div className="font-semibold text-slate-900 pl-3">DYNAMIC UNCERTAINTY CONE (Empirical 68% Position Error Envelope)</div>
            <div className="text-slate-400 pl-6">↓</div>
            <div className="font-semibold text-slate-900 pl-3">RISK & EXPOSURE ENGINE (UN UNDRR Multi-Criteria Framework: Hazard × Exposure × Vulnerability)</div>
            <div className="text-slate-400 pl-6">↓</div>
            <div className="font-semibold text-slate-900 pl-3">LOCATION INTELLIGENCE (Point-Click Micro-Dossier & Holland Local Wind Profile)</div>
            <div className="text-slate-400 pl-6">↓</div>
            <div className="font-bold text-slate-900 pl-3">ACTIONABLE DECISION-SUPPORT AI ADVISORIES (Civil Defense, Healthcare, Police, Public)</div>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white border border-slate-200 rounded p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search questions or keywords (e.g. persistence, leakage, CNN, risk)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded focus:outline-none focus:border-slate-400 text-slate-900 font-mono"
          />
        </div>

        <div className="flex items-center space-x-1 overflow-x-auto text-xs font-mono">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCat(cat)}
              className={`px-2.5 py-1 rounded text-xs transition ${
                selectedCat === cat
                  ? "bg-slate-900 text-white font-semibold"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Accordion Questions List */}
      <div className="space-y-2.5">
        {filtered.map((item) => {
          const isExpanded = expandedId === item.id;
          return (
            <div 
              key={item.id}
              className={`bg-white border rounded transition-all ${
                isExpanded 
                  ? "border-slate-400" 
                  : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <button
                onClick={() => setExpandedId(isExpanded ? null : item.id)}
                className="w-full p-3.5 text-left flex items-start justify-between gap-4"
              >
                <div className="flex items-start space-x-3">
                  <span className="w-5 h-5 rounded bg-slate-100 text-slate-700 font-mono text-xs font-semibold flex items-center justify-center shrink-0 mt-0.5 border border-slate-200">
                    {item.id}
                  </span>
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-0.5">
                      QUESTION • {item.category}
                    </span>
                    <h3 className="text-xs font-semibold text-slate-900 leading-snug">
                      {item.q}
                    </h3>
                  </div>
                </div>

                <div className="p-1 rounded text-slate-400 shrink-0">
                  {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 pt-2 space-y-3 border-t border-slate-100 text-xs">
                  <div>
                    <span className="text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                      ANSWER
                    </span>
                    <p className="text-slate-800 leading-relaxed font-sans">
                      {item.a}
                    </p>
                  </div>

                  <div className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-1 text-[11px] font-mono text-slate-600">
                    <span className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider block">
                      EVIDENCE
                    </span>
                    <div className="flex items-start space-x-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                      <span>{item.evidence}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
