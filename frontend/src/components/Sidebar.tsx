import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/morning-workflow", label: "Morning Workflow" },
  { to: "/board", label: "Board" },
  { to: "/flag-bridge", label: "Flag Bridge" },
  { to: "/risk-radar", label: "Risk Radar" },
  { to: "/operations-schedule", label: "Operations Schedule" },
  { to: "/report-operations", label: "Report Operations" },
  { to: "/ai-agent", label: "AI Agent" },
  { to: "/admin", label: "Admin" },
  { to: "/admin/unit-master", label: "Unit Master" },
];

export function Sidebar() {
  return (
    <aside className="border-b border-border bg-surface px-5 py-6 text-text lg:min-h-screen lg:border-b-0 lg:border-r">
      <div className="mb-8">
        <p className="text-[11px] font-medium uppercase tracking-[0.24em] text-muted">
          DMRB
        </p>
        <h1 className="mt-2 text-xl font-semibold tracking-tight text-text-strong">
          Operations Console
        </h1>
      </div>

      <nav className="space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/admin"}
            className={({ isActive }) =>
              `group relative block rounded-md px-3 py-2 text-sm transition ${
                isActive
                  ? "bg-surface-3 text-text-strong shadow-hairline"
                  : "text-muted hover:bg-surface-2 hover:text-text"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`absolute inset-y-1 left-0 w-[3px] rounded-full transition ${
                    isActive ? "bg-white" : "bg-transparent"
                  }`}
                />
                <span className="ml-2">{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

    </aside>
  );
}
