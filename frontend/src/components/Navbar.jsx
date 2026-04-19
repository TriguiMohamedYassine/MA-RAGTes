const ICON_GRID = (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
    <rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>
  </svg>
);
const ICON_FILE = (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14,2 14,8 20,8"/>
  </svg>
);
const ICON_CLOCK = (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/>
  </svg>
);
const ICON_GEAR = (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);
const ICON_GH = (
  <svg width="15" height="15" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.49.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.56 9.56 0 0 1 12 6.8c.85 0 1.71.11 2.51.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10.01 10.01 0 0 0 22 12c0-5.52-4.48-10-10-10z"/>
  </svg>
);

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: ICON_GRID },
  { id: "newtest",   label: "New Test",  icon: ICON_FILE },
  { id: "history",   label: "History",   icon: ICON_CLOCK },
  { id: "settings",  label: "Settings",  icon: ICON_GEAR },
];

export default function Navbar({ current, onChange }) {
  return (
    <nav style={{
      background: "white",
      borderBottom: "1px solid rgba(0,0,0,0.07)",
      padding: "0 2.5rem",
      display: "flex",
      alignItems: "center",
      gap: "4px",
      height: 62,
      position: "sticky",
      top: 0,
      zIndex: 100,
      boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginRight: "auto" }}>
        <div style={{
          width: 38, height: 38,
          borderRadius: 11,
          background: "linear-gradient(135deg, #7c3aed, #a855f7)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <svg width="20" height="20" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <div style={{ fontSize: 17, fontWeight: 600, color: "#7c3aed", lineHeight: 1.2 }}>MA-RAGTes</div>
          <div style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.2 }}>Multi-Agent Testing System</div>
        </div>
      </div>

      {/* Nav links */}
      {NAV_ITEMS.map(({ id, label, icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          style={{
            display: "flex", alignItems: "center", gap: 7,
            padding: "7px 14px",
            borderRadius: 9,
            border: "none",
            fontSize: 14,
            fontWeight: current === id ? 500 : 400,
            cursor: "pointer",
            fontFamily: "'DM Sans', sans-serif",
            background: current === id ? "#7c3aed" : "transparent",
            color: current === id ? "white" : "#64748b",
            transition: "all 0.15s",
          }}
          onMouseEnter={e => { if (current !== id) e.currentTarget.style.background = "#f1f5f9"; }}
          onMouseLeave={e => { if (current !== id) e.currentTarget.style.background = "transparent"; }}
        >
          {icon} {label}
        </button>
      ))}

      {/* GitHub */}
      <button className="btn" style={{ marginLeft: 8 }} onClick={() => window.open("https://github.com", "_blank")}>
        {ICON_GH} GitHub
      </button>
    </nav>
  );
}
