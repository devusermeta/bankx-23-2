import { Outlet, Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";

import { LoginButton } from "../../components/LoginButton";
import { Button } from "@/components/ui/button";
import { BarChart3 } from "lucide-react";
import { ThemeToggle } from "../../components/ThemeToggle/ThemeToggle";
import { getCurrentUserRole, canViewObservability, UserRole } from "../../lib/roleUtils";

const Layout = () => {
    const navigate = useNavigate();
    const [userRole, setUserRole] = useState<UserRole | null>(null);
    const [canSeeObservability, setCanSeeObservability] = useState(false);

    // Check user role on mount and when auth state changes
    useEffect(() => {
        const checkRole = () => {
            const role = getCurrentUserRole();
            setUserRole(role);
            setCanSeeObservability(canViewObservability(role));
        };

        checkRole();
        
        // Re-check on storage changes (when user logs in/out)
        window.addEventListener('storage', checkRole);
        return () => window.removeEventListener('storage', checkRole);
    }, []);

    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        <h3 className={styles.headerTitle}>BankX Assistant</h3>
                    </Link>
                    
                    <div className="flex items-center gap-3">
                        {canSeeObservability && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => navigate('/dashboard')}
                                className="flex items-center gap-2"
                                title="View observability metrics (Admin/Bank Teller only)"
                            >
                                <BarChart3 className="h-4 w-4" />
                                Observability Metrics
                            </Button>
                        )}
                        <ThemeToggle />
                        {useLogin && <LoginButton />}
                    </div>
                </div>
            </header>

            <Outlet />
        </div>
    );
};

export default Layout;
