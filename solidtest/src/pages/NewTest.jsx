import { useEffect, useMemo, useRef, useState } from "react";
import { getRunStatus, startRun } from "../services/api";

const ERC20_SNIPPET = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MyToken is ERC20 {
    constructor() ERC20("MyToken", "MTK") {
        _mint(msg.sender, 1_000_000 * 10 ** decimals());
    }
}`;

const ERC721_SNIPPET = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract MyNFT is ERC721 {
    uint256 private _tokenIdCounter;

    constructor() ERC721("MyNFT", "NFT") {}

    function safeMint(address to) public {
        _safeMint(to, _tokenIdCounter++);
    }
}`;

const CUSTOM_SNIPPET = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CustomContract {
    address public owner;
    uint256 public value;

    constructor() {
        owner = msg.sender;
    }

    function setValue(uint256 newValue) external {
        require(msg.sender == owner, "Not owner");
        value = newValue;
    }
}`;

const PIPELINE_STEPS = [
  { key: "test_designer", label: "Test Designer", description: "Analyzes contract and detects standards" },
  { key: "generator_normal", label: "Generator", description: "Generates tests using LLM pipeline" },
  { key: "executor", label: "Executor", description: "Runs tests with Hardhat" },
  { key: "analyzer", label: "Analyzer", description: "Analyzes failures and coverage" },
  { key: "evaluator", label: "Evaluator", description: "Decides continue or stop" },
  { key: "corrector", label: "Corrector", description: "Fixes failing tests if needed" },
];

const GRAPH_STEPS = [
  { key: "test_designer", label: "Test Designer" },
  { key: "generator_normal", label: "Generator" },
  { key: "executor", label: "Executor" },
  { key: "analyzer", label: "Analyzer" },
  { key: "evaluator", label: "Evaluator" },
];

const ACTIVE_RUN_STORAGE_KEY = "solidtest_active_run_id";

const STEP_INDEX = Object.fromEntries(PIPELINE_STEPS.map((step, index) => [step.key, index]));
const LOOP_KEYS = ["executor", "analyzer", "evaluator", "corrector"];
const GRAPH_NODE_LAYOUT = {
  test_designer: { x: 30, y: 122 },
  generator_normal: { x: 230, y: 122 },
  executor: { x: 430, y: 122 },
  analyzer: { x: 630, y: 122 },
  evaluator: { x: 830, y: 210 },
};

const GRAPH_EDGES = [
  { from: "test_designer", to: "generator_normal", curve: "M 120 158 L 230 158" },
  { from: "generator_normal", to: "executor", curve: "M 320 158 L 430 158" },
  { from: "executor", to: "analyzer", curve: "M 520 158 L 630 158" },
  { from: "analyzer", to: "evaluator", curve: "M 720 170 C 770 180, 810 206, 830 246" },
  { from: "evaluator", to: "generator_normal", curve: "M 830 246 C 730 302, 360 300, 275 194" },
];

function normalizeNode(node) {
  if (!node) return "";
  if (node === "increment") return "corrector";
  if (node === "starting") return "test_designer";
  if (node === "finished") return "finished";
  return node;
}

function stepDotColor(state) {
  if (state === "done") return "#22c55e";
  if (state === "active") return "#7c3aed";
  if (state === "error") return "#ef4444";
  return "#cbd5e1";
}

function edgeColor(fromState, toState) {
  if (fromState === "error" || toState === "error") return "#ef4444";
  if (fromState === "active" || toState === "active") return "#7c3aed";
  if (fromState === "done" && toState === "done") return "#22c55e";
  return "#94a3b8";
}

function getLinearState(index, currentIndex, pipelineStatus) {
  if (pipelineStatus === "done") return "done";
  if (pipelineStatus === "error") {
    if (currentIndex === -1) return "pending";
    if (index < currentIndex) return "done";
    if (index === currentIndex) return "error";
    return "pending";
  }
  if (currentIndex === -1) return "pending";
  if (index < currentIndex) return "done";
  if (index === currentIndex) return "active";
  return "pending";
}

function getLoopAwareStepStates(currentNode, pipelineStatus) {
  const normalized = normalizeNode(currentNode);
  const currentIndex = STEP_INDEX[normalized] ?? -1;

  if (pipelineStatus === "done") {
    return PIPELINE_STEPS.map(() => "done");
  }

  if (pipelineStatus === "error") {
    return PIPELINE_STEPS.map((_, index) => getLinearState(index, currentIndex, pipelineStatus));
  }

  // Before entering the iterative loop, linear progression is enough.
  if (!LOOP_KEYS.includes(normalized)) {
    return PIPELINE_STEPS.map((_, index) => getLinearState(index, currentIndex, pipelineStatus));
  }

  const loopStates = {
    executor: ["active", "pending", "pending", "pending"],
    analyzer: ["done", "active", "pending", "pending"],
    evaluator: ["done", "done", "active", "pending"],
    corrector: ["done", "done", "done", "active"],
  };

  const states = PIPELINE_STEPS.map(() => "pending");

  // Steps before executor are global setup steps and stay done once loop is running.
  states[STEP_INDEX.test_designer] = "done";
  states[STEP_INDEX.generator_normal] = "done";

  const segment = loopStates[normalized] || ["pending", "pending", "pending", "pending"];
  LOOP_KEYS.forEach((key, i) => {
    states[STEP_INDEX[key]] = segment[i];
  });

  return states;
}

export default function NewTest({ onRunStarted }) {
  const [contractName, setContractName] = useState("");
  const [userStory, setUserStory] = useState("");
  const [code, setCode] = useState("");
  const [fileName, setFileName] = useState("");
  const [uploadMode, setUploadMode] = useState("paste");
  const [showAdvanced, setShowAdvanced] = useState(true);
  const [maxRetries, setMaxRetries] = useState(7);
  const [statementCoverage, setStatementCoverage] = useState(85);
  const [branchCoverage, setBranchCoverage] = useState(80);
  const [ragEnabled, setRagEnabled] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [activeRunId, setActiveRunId] = useState("");
  const [pipelineStatus, setPipelineStatus] = useState("idle");
  const [currentNode, setCurrentNode] = useState("");
  const [runIterations, setRunIterations] = useState(0);

  const fileInputRef = useRef(null);

  const canSubmit = useMemo(() => !isSubmitting && code.trim().length > 0, [isSubmitting, code]);

  const syncRunStatus = async (runId) => {
    const status = await getRunStatus(runId);
    const statusValue = status?.status || "running";
    setPipelineStatus(statusValue);
    setCurrentNode(status?.current_node || (statusValue === "done" ? "finished" : ""));
    setRunIterations(Number(status?.iterations || 0));
    if (statusValue === "done" || statusValue === "error") {
      localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
    }
  };

  const stepStates = useMemo(
    () => getLoopAwareStepStates(currentNode, pipelineStatus),
    [currentNode, pipelineStatus],
  );

  const normalizedCurrentNode = normalizeNode(currentNode);
  const hasReturnLoop = runIterations > 0;
  const showCorrectionLoop = hasReturnLoop;
  const isReturnTransition = pipelineStatus === "running" && normalizedCurrentNode === "corrector";
  const activeGraphNode = useMemo(() => {
    if (isReturnTransition) return "generator_normal";
    if (GRAPH_STEPS.some((step) => step.key === normalizedCurrentNode)) return normalizedCurrentNode;
    return "";
  }, [isReturnTransition, normalizedCurrentNode]);
  const stepStateByKey = useMemo(
    () => Object.fromEntries(PIPELINE_STEPS.map((step, index) => [step.key, stepStates[index]])),
    [stepStates],
  );
  const graphStateByKey = useMemo(
    () => {
      if (isReturnTransition) {
        return {
          test_designer: stepStateByKey.test_designer,
          generator_normal: "active",
          executor: "pending",
          analyzer: "pending",
          evaluator: "error",
        };
      }

      return {
        test_designer: stepStateByKey.test_designer,
        generator_normal: hasReturnLoop ? stepStateByKey.corrector : stepStateByKey.generator_normal,
        executor: stepStateByKey.executor,
        analyzer: stepStateByKey.analyzer,
        evaluator: stepStateByKey.evaluator,
      };
    },
    [hasReturnLoop, isReturnTransition, stepStateByKey],
  );

  useEffect(() => {
    if (!activeRunId || pipelineStatus !== "running") return undefined;

    let cancelled = false;

    const poll = async () => {
      try {
        if (cancelled) return;
        await syncRunStatus(activeRunId);
      } catch (err) {
        if (cancelled) return;
        setPipelineStatus("error");
        setError(err instanceof Error ? err.message : "Erreur lors du suivi du pipeline.");
      }
    };

    void poll();
    const id = setInterval(() => {
      void poll();
    }, 400);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [activeRunId, pipelineStatus]);

  useEffect(() => {
    const storedRunId = localStorage.getItem(ACTIVE_RUN_STORAGE_KEY);
    if (!storedRunId) return;

    let cancelled = false;
    const restore = async () => {
      try {
        if (cancelled) return;
        setActiveRunId(storedRunId);
        await syncRunStatus(storedRunId);
      } catch {
        localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
      }
    };

    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadPreset = (kind) => {
    if (kind === "erc20") {
      setCode(ERC20_SNIPPET);
      setContractName("MyToken");
    }
    if (kind === "erc721") {
      setCode(ERC721_SNIPPET);
      setContractName("MyNFT");
    }
    if (kind === "custom") {
      setCode(CUSTOM_SNIPPET);
      setContractName("CustomContract");
    }
    setUploadMode("paste");
    setFileName("");
    setError("");
  };

  const onFilePicked = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".sol")) {
      setError("Le fichier doit avoir l'extension .sol");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result;
        if (typeof text === "string") {
          setCode(text);
          setFileName(file.name);
          setError("");
          if (!contractName) {
            setContractName(file.name.replace(/\.sol$/i, ""));
          }
        }
      } catch {
        setError("Erreur lors de la lecture du fichier.");
      }
    };
    reader.onerror = () => {
      setError("Impossible de lire le fichier.");
    };
    reader.readAsText(file);
  };

  const handleSubmit = async () => {
    if (!code.trim()) {
      setError("Le code du contrat est obligatoire.");
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      const payload = {
        contract_code: code,
        contract_name: contractName.trim(),
        user_story: userStory,
      };
      const run = await startRun(payload);
      setActiveRunId(run.run_id);
      setPipelineStatus(run.status || "running");
      setCurrentNode("starting");
      setRunIterations(0);
      localStorage.setItem(ACTIVE_RUN_STORAGE_KEY, run.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue lors du lancement.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-title">Create New Test Suite</div>
      <div className="page-sub">Submit your Solidity smart contract to generate comprehensive unit tests automatically.</div>

      <div style={{ marginBottom: "1rem" }}>
        <div className="card" style={{ padding: "1.25rem" }}>
          <div className="newtest-panel-title" style={{ marginBottom: 4 }}>Contract Information</div>
          <div style={{ color: "#64748b", marginBottom: "1rem" }}>Provide your smart contract details</div>

          <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 6 }}>Contract Name</label>
          <input
            type="text"
            value={contractName}
            onChange={(event) => setContractName(event.target.value)}
            placeholder="e.g., MyToken, NFTMarketplace"
            style={{ marginBottom: "1rem" }}
          />

          <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 6 }}>Upload Method</label>
          <div style={{ display: "flex", marginBottom: "0.75rem", background: "#e5e7eb", borderRadius: 999, padding: 4 }}>
            <button
              type="button"
              className="btn"
              onClick={() => setUploadMode("paste")}
              style={{
                flex: 1,
                justifyContent: "center",
                borderRadius: 999,
                border: "none",
                background: uploadMode === "paste" ? "#ffffff" : "transparent",
                boxShadow: uploadMode === "paste" ? "var(--shadow-sm)" : "none",
              }}
            >
              Paste Code
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => fileInputRef.current?.click()}
              style={{
                flex: 1,
                justifyContent: "center",
                borderRadius: 999,
                border: "none",
                background: uploadMode === "file" ? "#ffffff" : "transparent",
                boxShadow: uploadMode === "file" ? "var(--shadow-sm)" : "none",
              }}
            >
              Upload File
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".sol"
              onChange={(event) => {
                setUploadMode("file");
                onFilePicked(event);
              }}
              style={{ display: "none" }}
            />
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: "0.75rem", flexWrap: "wrap" }}>
            <button className="btn" onClick={() => loadPreset("erc20")}>Load ERC20</button>
            <button className="btn" onClick={() => loadPreset("erc721")}>Load ERC721</button>
            <button className="btn" onClick={() => loadPreset("custom")}>Load Custom</button>
          </div>

          {fileName && (
            <div style={{ fontSize: 12, color: "#475569", marginBottom: "0.75rem" }}>
              Selected file: {fileName}
            </div>
          )}

          <textarea
            value={code}
            onChange={(event) => {
              setUploadMode("paste");
              setCode(event.target.value);
            }}
            placeholder="pragma solidity ^0.8.0;"
            style={{
              minHeight: 250,
              marginBottom: "0.75rem",
              background: "#12141a",
              color: "#e2e8f0",
              border: "none",
              fontFamily: "'Space Mono', monospace",
              lineHeight: 1.6,
            }}
          />

          <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 6 }}>User Story / Specs</label>
          <textarea
            value={userStory}
            onChange={(event) => setUserStory(event.target.value)}
            placeholder="Describe business rules and expected behaviors"
            style={{ minHeight: 100 }}
          />
        </div>
      </div>

      <div className="card" style={{ padding: "1.25rem", marginBottom: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1rem" }}>
          <div>
            <div className="newtest-panel-title">Advanced Settings</div>
            <div style={{ color: "#64748b" }}>Configure test generation parameters</div>
          </div>
          <button
            type="button"
            className={`toggle-switch ${showAdvanced ? "on" : ""}`}
            onClick={() => setShowAdvanced((previous) => !previous)}
            aria-label="Toggle advanced settings"
          />
        </div>

        {showAdvanced && (
          <div>
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontWeight: 600 }}>Max Retry Iterations</span>
                <span style={{ fontWeight: 700 }}>{maxRetries}</span>
              </div>
              <input type="range" min={1} max={12} value={maxRetries} onChange={(event) => setMaxRetries(Number(event.target.value))} />
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontWeight: 600 }}>Statement Coverage Threshold</span>
                <span style={{ fontWeight: 700 }}>{statementCoverage}%</span>
              </div>
              <input
                type="range"
                min={50}
                max={100}
                value={statementCoverage}
                onChange={(event) => setStatementCoverage(Number(event.target.value))}
              />
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontWeight: 600 }}>Branch Coverage Threshold</span>
                <span style={{ fontWeight: 700 }}>{branchCoverage}%</span>
              </div>
              <input type="range" min={40} max={100} value={branchCoverage} onChange={(event) => setBranchCoverage(Number(event.target.value))} />
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontWeight: 600 }}>Enable RAG System</div>
                <div style={{ color: "#64748b", fontSize: 13 }}>Use ChromaDB for standard detection</div>
              </div>
              <button
                type="button"
                className={`toggle-switch ${ragEnabled ? "on" : ""}`}
                onClick={() => setRagEnabled((previous) => !previous)}
                aria-label="Toggle RAG"
              />
            </div>
          </div>
        )}
      </div>

      <div className="card" style={{ padding: "1.25rem", borderColor: "#c7d2fe", background: "#f8f7ff", marginBottom: "1rem" }}>
        <div className="newtest-panel-title" style={{ marginBottom: "0.85rem" }}>Pipeline Progress</div>

        <div style={{ display: "flex", gap: 8, marginBottom: "0.9rem", flexWrap: "wrap" }}>
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={!canSubmit}
            style={{ opacity: canSubmit ? 1 : 0.6, cursor: canSubmit ? "pointer" : "not-allowed" }}
          >
            {isSubmitting ? "Starting..." : "Generate Tests"}
          </button>
          {activeRunId && (
            <button className="btn" onClick={() => onRunStarted && onRunStarted(activeRunId)}>
              Open in History
            </button>
          )}
        </div>

        <div style={{ marginBottom: "0.75rem", width: "100%" }}>
          <div style={{ width: "100%", position: "relative" }}>
            <svg width="100%" height="320" viewBox="0 0 950 320" fill="none" role="img" aria-label="Pipeline graph" preserveAspectRatio="xMidYMid meet">
              <defs>
                <marker id="arrow-head" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0,0 L8,4 L0,8 Z" fill="#64748b" />
                </marker>
              </defs>

              {GRAPH_EDGES.map((edge) => {
                const isReturnEdge = edge.from === "evaluator" && edge.to === "generator_normal";
                const touchesLoopNodes = ["executor", "analyzer", "evaluator"].includes(edge.from)
                  || ["executor", "analyzer", "evaluator"].includes(edge.to);
                const isIncomingToActive = edge.to === activeGraphNode && graphStateByKey[activeGraphNode] === "active";

                let edgeStroke;
                if (isReturnEdge) {
                  edgeStroke = hasReturnLoop ? "#22c55e" : "#cbd5e1";
                } else if (isReturnTransition && touchesLoopNodes) {
                  edgeStroke = "#cbd5e1";
                } else if (isIncomingToActive) {
                  edgeStroke = "#22c55e";
                } else {
                  edgeStroke = edgeColor(graphStateByKey[edge.from], graphStateByKey[edge.to]);
                }

                return (
                  <path
                    key={`${edge.from}-${edge.to}`}
                    d={edge.curve}
                    stroke={edgeStroke}
                    strokeWidth="2.5"
                    strokeDasharray={edge.from === "evaluator" ? "7 6" : "0"}
                    markerEnd="url(#arrow-head)"
                  />
                );
              })}

                {GRAPH_STEPS.map((step, index) => {
                const pos = GRAPH_NODE_LAYOUT[step.key];
                  const state = graphStateByKey[step.key] || "pending";
                  const displayLabel = step.key === "generator_normal" && hasReturnLoop ? "Corrector" : step.label;
                if (!pos) return null;

                return (
                  <g key={step.key} transform={`translate(${pos.x}, ${pos.y})`}>
                    <rect
                      x="0"
                      y="0"
                      width="90"
                      height="72"
                      rx="12"
                      fill={state === "pending" ? "#ffffff" : state === "active" ? "#f5f3ff" : "#f8fafc"}
                      stroke={stepDotColor(state)}
                      strokeWidth="2"
                    />
                    <circle cx="16" cy="16" r="9" fill={stepDotColor(state)} />
                    <text x="16" y="19" textAnchor="middle" fontSize="10" fill="#ffffff" fontWeight="700">
                      {index + 1}
                    </text>
                    <text x="12" y="38" fontSize="10" fill="#0f172a" fontWeight="700">
                      {displayLabel}
                    </text>
                    <text x="12" y="53" fontSize="9" fill="#64748b">
                      {state}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {showCorrectionLoop && (
          <div
            className="card"
            style={{
              marginTop: "0.2rem",
              marginBottom: "0.7rem",
              padding: "0.6rem 0.7rem",
              background: normalizedCurrentNode === "corrector" ? "#ede9fe" : "#f8fafc",
              borderColor: normalizedCurrentNode === "corrector" ? "#c4b5fd" : "#dbeafe",
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 700, color: "#4c1d95", marginBottom: 2 }}>Loop Detected</div>
            <div style={{ fontSize: 12, color: "#475569" }}>
              Return path: <strong>Evaluator -&gt; Generator (Corrector mode) -&gt; Executor</strong> (retry #{runIterations})
            </div>
            <div style={{ fontSize: 12, color: "#64748b" }}>
              On retries, the Generator node switches to Corrector mode.
            </div>
          </div>
        )}

        {activeRunId && (
          <div className="card" style={{ marginTop: "0.8rem", padding: "0.7rem", background: "#ffffff" }}>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Run ID</div>
            <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 12, marginBottom: 6 }}>{activeRunId}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: pipelineStatus === "error" ? "#b91c1c" : "#334155" }}>
              Status: {pipelineStatus} {currentNode ? `- ${currentNode}` : ""}
            </div>
            <div style={{ fontSize: 12, color: "#64748b" }}>Iterations: {runIterations}</div>
          </div>
        )}
      </div>

      {error && (
        <div className="card" style={{ padding: "0.9rem 1rem", marginBottom: "1rem", borderColor: "#fecaca", color: "#b91c1c" }}>
          {error}
        </div>
      )}

      {activeRunId && (
        <div className="card" style={{ padding: "0.9rem 1rem", marginBottom: "1rem", borderColor: "#bbf7d0", color: "#166534" }}>
          Run lancé avec succès: <strong>{activeRunId}</strong>
        </div>
      )}
    </div>
  );
}
