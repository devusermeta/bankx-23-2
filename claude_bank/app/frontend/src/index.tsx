import React from "react";
import ReactDOM from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication, EventType, AccountInfo } from "@azure/msal-browser";
import { msalConfig, useLogin } from "./authConfig";

import "./index.css";

import Layout from "./pages/layout/Layout";
import Chat from "./pages/chat/Chat";
import ChatNew from "./pages/chat/ChatNew";
import DashboardLayout from "./pages/dashboard/DashboardLayout";
import DashboardOverview from "./pages/dashboard/DashboardOverview";
import { ConversationsPage } from "./pages/dashboard/ConversationsPage";
import AgentDecisionsPage from "./pages/dashboard/AgentDecisionsPage";
import RagEvaluationsPage from "./pages/dashboard/RagEvaluationsPage";
import TriageRulesPage from "./pages/dashboard/TriageRulesPage";
import McpAuditPage from "./pages/dashboard/McpAuditPage";
import UserMessagesPage from "./pages/dashboard/UserMessagesPage";

// Log token information from localStorage on app startup
// console.log("=".repeat(80));
// console.log("🚀 APP STARTING - Reading token from localStorage...");
// console.log("=".repeat(80));

for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.includes('accesstoken')) {
        // console.log(`🔑 Found token key: ${key}`);
        const value = localStorage.getItem(key);
        if (value) {
            try {
                const parsed = JSON.parse(value);
                // console.log("📜 Token object:", parsed);
                if (parsed.secret) {
                    // console.log("🎫 ACCESS TOKEN:", parsed.secret);
                    
                    // Decode the token
                    const base64Url = parsed.secret.split('.')[1];
                    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                    }).join(''));
                    const decoded = JSON.parse(jsonPayload);
                    // console.log("🎭 DECODED TOKEN:", decoded);
                    console.log("👤 User:", decoded.preferred_username || decoded.upn || decoded.email);
                    console.log("🎯 ROLES:", decoded.roles || "⚠️ No roles in token");
                }
            } catch (e) {
                console.error("❌ Failed to parse token:", e);
            }
        }
    }
}
// console.log("=".repeat(80));

var layout;
if (useLogin) {
    var msalInstance = new PublicClientApplication(msalConfig);

    // CRITICAL: Initialize MSAL before any operations
    await msalInstance.initialize();

    // Default to using the first account if no account is active on page load
    if (!msalInstance.getActiveAccount() && msalInstance.getAllAccounts().length > 0) {
        // Account selection logic is app dependent. Adjust as needed for different use cases.
        msalInstance.setActiveAccount(msalInstance.getAllAccounts()[0]);
    }

    // Listen for sign-in event and set active account
    msalInstance.addEventCallback(event => {
        if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
            const account = event.payload as AccountInfo;
            msalInstance.setActiveAccount(account);
        }
    });

    layout = (
        <MsalProvider instance={msalInstance}>
            <Layout />
        </MsalProvider>
    );
} else {
    layout = <Layout />;
}

initializeIcons();

const router = createHashRouter([
    {
        path: "/",
        element: layout,
        children: [
            {
                index: true,
                element: <ChatNew />
            },
            {
                path: "*",
                lazy: () => import("./pages/NoPage")
            }
        ]
    },
    {
        path: "/dashboard",
        element: <DashboardLayout />,
        children: [
            {
                index: true,
                element: <DashboardOverview />
            },
            {
                path: "agent-decisions",
                element: <AgentDecisionsPage />
            },
            {
                path: "rag-evaluations",
                element: <RagEvaluationsPage />
            },
            {
                path: "triage-rules",
                element: <TriageRulesPage />
            },
            {
                path: "mcp-audit",
                element: <McpAuditPage />
            },
            {
                path: "user-messages",
                element: <UserMessagesPage />
            },
            {
                path: "conversations",
                element: <ConversationsPage />
            }
        ]
    }
]);

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
        <RouterProvider router={router} />
    </React.StrictMode>
);
