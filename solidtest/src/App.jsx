import { useState } from "react";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import NewTest from "./pages/NewTest";
import History from "./pages/History";
import Settings from "./pages/Settings";
import "./index.css";

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [selectedRunId, setSelectedRunId] = useState("");
  const [historyOpenToken, setHistoryOpenToken] = useState(0);

  const openHistory = (runId = "") => {
    setSelectedRunId(runId);
    setHistoryOpenToken((previous) => previous + 1);
    setPage("history");
  };

  const renderPage = () => {
    switch (page) {
      case "dashboard": return <Dashboard onNewTest={() => setPage("newtest")} onOpenHistory={openHistory} />;
      case "newtest":   return <NewTest onRunStarted={openHistory} />;
      case "history":   return <History selectedRunId={selectedRunId} navigationToken={historyOpenToken} onNewTest={() => setPage("newtest")} />;
      case "settings":  return <Settings />;
      default:          return <Dashboard onNewTest={() => setPage("newtest")} onOpenHistory={openHistory} />;
    }
  };

  return (
    <div className="app">
      <Navbar current={page} onChange={setPage} />
      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  );
}
