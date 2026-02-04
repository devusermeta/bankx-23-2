import { Outlet, NavLink } from "react-router-dom";
import { 
  LayoutDashboard, 
  Activity, 
  MessageSquare, 
  BarChart3
} from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle/ThemeToggle";
import styles from "./DashboardLayout.module.css";

const DashboardLayout = () => {

  return (
    <div className="min-h-screen bg-background">
      {/* Top Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/50">
        <div className="flex h-16 items-center px-6">
          <div className="flex items-center gap-3">
            <LayoutDashboard className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-500 to-purple-600 bg-clip-text text-transparent">
              BankX Operations Dashboard
            </h1>
          </div>
          
          <div className="ml-auto flex items-center gap-4">
            <ThemeToggle />
            
            <NavLink to="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              ← Back to Chat
            </NavLink>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar Navigation */}
        <aside className="w-64 border-r border-border bg-card/30 min-h-[calc(100vh-4rem)] p-4">
          <nav className="space-y-2">
            <NavLink
              to="/dashboard"
              end
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <LayoutDashboard className="h-4 w-4" />
              Overview
            </NavLink>

            <div className="pt-4 pb-2">
              <div className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Observability
              </div>
            </div>

            <NavLink
              to="/dashboard/agent-decisions"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <Activity className="h-4 w-4" />
              Agent Decisions
            </NavLink>

            {/* <NavLink
              to="/dashboard/rag-evaluations"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <BarChart3 className="h-4 w-4" />
              RAG Evaluations
            </NavLink> */}

            <NavLink
              to="/dashboard/triage-rules"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <Activity className="h-4 w-4" />
              Triage Rules
            </NavLink>

            <NavLink
              to="/dashboard/mcp-audit"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <Activity className="h-4 w-4" />
              MCP Audit Trail
            </NavLink>

            {/* <NavLink
              to="/dashboard/user-messages"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <MessageSquare className="h-4 w-4" />
              User Messages
            </NavLink> */}

            <div className="pt-4 pb-2">
              <div className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Data
              </div>
            </div>

            <NavLink
              to="/dashboard/conversations"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`
              }
            >
              <MessageSquare className="h-4 w-4" />
              Conversations
            </NavLink>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
