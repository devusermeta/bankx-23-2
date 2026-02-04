import { DefaultButton } from "@fluentui/react";
import { useMsal } from "@azure/msal-react";

import styles from "./LoginButton.module.css";
import { getRedirectUri, loginRequest } from "../../authConfig";

export const LoginButton = () => {
    const { instance } = useMsal();
    const activeAccount = instance.getActiveAccount();
    const handleLoginRedirect = () => {
        /**
         * Using redirect flow instead of popup to avoid CORS and popup blocker issues
         */
        instance
            .loginRedirect({
                ...loginRequest,
                redirectUri: getRedirectUri()
            })
            .catch(error => console.log(error));
    };
    const handleLogoutRedirect = () => {
        instance
            .logoutRedirect({
                postLogoutRedirectUri: "/", // redirects the top level app after logout
                account: instance.getActiveAccount()
            })
            .catch(error => console.log(error));
    };
    const logoutText = `Logout\n${activeAccount?.username}`;
    return (
        <DefaultButton
            text={activeAccount ? logoutText : "Login"}
            className={styles.loginButton}
            onClick={activeAccount ? handleLogoutRedirect : handleLoginRedirect}
        ></DefaultButton>
    );
};
