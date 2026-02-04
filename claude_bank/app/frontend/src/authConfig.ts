// Refactored from https://github.com/Azure-Samples/ms-identity-javascript-react-tutorial/blob/main/1-Authentication/1-sign-in/SPA/src/authConfig.js

import { AuthenticationResult, IPublicClientApplication } from "@azure/msal-browser";

const BACKEND_URI = import.meta.env.VITE_BACKEND_URI ? import.meta.env.VITE_BACKEND_URI : "";

interface AuthSetup {
    // Set to true if login elements should be shown in the UI
    useLogin: boolean;
    /**
     * Configuration object to be passed to MSAL instance on creation.
     * For a full list of MSAL.js configuration parameters, visit:
     * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
     */
    msalConfig: {
        auth: {
            clientId: string; // Client app id used for login
            authority: string; // Directory to use for login https://learn.microsoft.com/azure/active-directory/develop/msal-client-application-configuration#authority
            redirectUri: string; // Points to window.location.origin. You must register this URI on Azure Portal/App Registration.
            postLogoutRedirectUri: string; // Indicates the page to navigate after logout.
            navigateToLoginRequestUrl: boolean; // If "true", will navigate back to the original request location before processing the auth code response.
        };
        cache: {
            cacheLocation: string; // Configures cache location. "sessionStorage" is more secure, but "localStorage" gives you SSO between tabs.
            storeAuthStateInCookie: boolean; // Set this to "true" if you are having issues on IE11 or Edge
        };
    };
    loginRequest: {
        /**
         * Scopes you add here will be prompted for user consent during sign-in.
         * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
         * For more information about OIDC scopes, visit:
         * https://docs.microsoft.com/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
         */
        scopes: Array<string>;
    };
    tokenRequest: {
        scopes: Array<string>;
    };
}

// Fetch the auth setup JSON data from the API if not already cached
async function fetchAuthSetup(): Promise<AuthSetup> {
    const response = await fetch(`${BACKEND_URI}/auth_setup`);
    if (!response.ok) {
        throw new Error(`auth setup response was not ok: ${response.status}`);
    }
    return await response.json();
}

const authSetup = await fetchAuthSetup();

export const useLogin = authSetup.useLogin;

/**
 * Configuration object to be passed to MSAL instance on creation.
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig = authSetup.msalConfig;

/**
 * Scopes you add here will be prompted for user consent during sign-in.
 * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
 * For more information about OIDC scopes, visit:
 * https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
 */
export const loginRequest = authSetup.loginRequest;

const tokenRequest = authSetup.tokenRequest;

// Build an absolute redirect URI using the current window's location and the relative redirect URI from auth setup
export const getRedirectUri = () => {
    return window.location.origin + authSetup.msalConfig.auth.redirectUri;
};

// Get an access token for use with the API server.
// ID token received when logging in may not be used for this purpose because it has the incorrect audience
export const getToken = async (client: IPublicClientApplication): Promise<AuthenticationResult | undefined> => {
    try {
        const account = client.getActiveAccount();
        if (!account) {
            console.warn("[AUTH] No active account found");
            return undefined;
        }

        // Try to get token silently first with forceRefresh if needed
        return await client.acquireTokenSilent({
            ...tokenRequest,
            redirectUri: getRedirectUri(),
            account: account,
            // Force refresh if token is close to expiration (within 5 minutes)
            forceRefresh: false
        });
    } catch (error: any) {
        console.warn("[AUTH] Silent token acquisition failed:", error.name, error.message);
        
        // If interaction is required, try popup as fallback
        if (error.name === "InteractionRequiredAuthError") {
            console.log("[AUTH] ⚠️ Token expired, attempting interactive re-authentication...");
            
            try {
                // Try to acquire token with popup (returns a promise with token)
                return await client.acquireTokenPopup({
                    ...tokenRequest,
                    redirectUri: getRedirectUri(),
                    prompt: "none" // Try silent authentication first
                });
            } catch (popupError: any) {
                console.error("[AUTH] ❌ Interactive re-authentication failed:", popupError);
                
                // Only log out after all attempts fail
                console.error("[AUTH] Logging out user after failed token refresh...");
                await client.logoutPopup({
                    postLogoutRedirectUri: "/",
                });
                
                return undefined;
            }
        }
        
        console.error("[AUTH] Token acquisition failed:", error);
        return undefined;
    }
};

// Check if the user has a valid token - useful for proactive validation
export const validateToken = async (client: IPublicClientApplication): Promise<boolean> => {
    try {
        const result = await getToken(client);
        if (result) {
            // Log token expiration for debugging
            const expiresOn = result.expiresOn;
            if (expiresOn) {
                const timeUntilExpiry = expiresOn.getTime() - Date.now();
                const minutesUntilExpiry = Math.floor(timeUntilExpiry / 60000);
                console.log(`[AUTH] ✅ Token valid for ${minutesUntilExpiry} more minutes`);
            }
        }
        return result !== undefined;
    } catch {
        return false;
    }
};

// Check if token needs refresh (within 5 minutes of expiration)
export const shouldRefreshToken = (result: AuthenticationResult): boolean => {
    if (!result.expiresOn) return false;
    const timeUntilExpiry = result.expiresOn.getTime() - Date.now();
    const minutesUntilExpiry = timeUntilExpiry / 60000;
    return minutesUntilExpiry < 5; // Refresh if less than 5 minutes remaining
};
