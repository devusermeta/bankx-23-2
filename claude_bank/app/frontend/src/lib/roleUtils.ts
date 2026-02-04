/**
 * Role-based Access Control Utilities
 * Handles JWT token role extraction and permission checking
 */

export enum UserRole {
    ADMIN = 'admin',
    USER = 'user',
    BANK_TELLER = 'bank_teller'
}

export interface TokenClaims {
    roles?: string[];
    role?: string;
    [key: string]: any;
}

/**
 * Extract role from JWT token claims
 * @param token JWT token string
 * @returns User role or null if not found
 */
export const extractRoleFromToken = (token: string): UserRole | null => {
    try {
        // JWT tokens have 3 parts separated by dots: header.payload.signature
        const parts = token.split('.');
        if (parts.length !== 3) {
            console.error('Invalid JWT token format');
            return null;
        }

        // Decode the payload (second part)
        const payload = parts[1];
        const decodedPayload = JSON.parse(atob(payload));
        
        // Check for role in different claim formats
        const role = decodedPayload.role || 
                    decodedPayload.roles?.[0] || 
                    decodedPayload['http://schemas.microsoft.com/ws/2008/06/identity/claims/role'] ||
                    decodedPayload['extension_Role'];

        if (!role) {
            console.warn('No role found in token claims');
            return null;
        }

        // Normalize role to lowercase and match enum
        const normalizedRole = role.toLowerCase();
        
        if (Object.values(UserRole).includes(normalizedRole as UserRole)) {
            return normalizedRole as UserRole;
        }

        console.warn(`Unknown role: ${role}`);
        return null;
    } catch (error) {
        console.error('Error extracting role from token:', error);
        return null;
    }
};

/**
 * Extract all claims from JWT token
 * @param token JWT token string
 * @returns Token claims object or null if invalid
 */
export const extractTokenClaims = (token: string): TokenClaims | null => {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) {
            return null;
        }

        const payload = parts[1];
        const decodedPayload = JSON.parse(atob(payload));
        return decodedPayload;
    } catch (error) {
        console.error('Error extracting token claims:', error);
        return null;
    }
};

/**
 * Permission definitions for different features
 */
export const Permissions = {
    VIEW_OBSERVABILITY: 'view_observability',
    MANAGE_USERS: 'manage_users',
    APPROVE_TRANSACTIONS: 'approve_transactions',
    VIEW_ALL_ACCOUNTS: 'view_all_accounts',
    ACCESS_ADMIN_PANEL: 'access_admin_panel'
} as const;

export type Permission = typeof Permissions[keyof typeof Permissions];

/**
 * Role-to-permissions mapping
 */
const rolePermissions: Record<UserRole, Permission[]> = {
    [UserRole.ADMIN]: [
        Permissions.VIEW_OBSERVABILITY,
        Permissions.MANAGE_USERS,
        Permissions.APPROVE_TRANSACTIONS,
        Permissions.VIEW_ALL_ACCOUNTS,
        Permissions.ACCESS_ADMIN_PANEL
    ],
    [UserRole.BANK_TELLER]: [
        Permissions.VIEW_OBSERVABILITY,
        Permissions.APPROVE_TRANSACTIONS,
        Permissions.VIEW_ALL_ACCOUNTS
    ],
    [UserRole.USER]: []
};

/**
 * Check if a role has a specific permission
 * @param role User role
 * @param permission Permission to check
 * @returns true if role has permission
 */
export const hasPermission = (role: UserRole | null, permission: Permission): boolean => {
    if (!role) return false;
    return rolePermissions[role]?.includes(permission) ?? false;
};

/**
 * Check if user can view observability metrics
 * @param role User role
 * @returns true if user can view observability
 */
export const canViewObservability = (role: UserRole | null): boolean => {
    return hasPermission(role, Permissions.VIEW_OBSERVABILITY);
};

/**
 * Check if user is admin
 * @param role User role
 * @returns true if user is admin
 */
export const isAdmin = (role: UserRole | null): boolean => {
    return role === UserRole.ADMIN;
};

/**
 * Check if user is bank teller or admin
 * @param role User role
 * @returns true if user is bank teller or admin
 */
export const isBankStaff = (role: UserRole | null): boolean => {
    return role === UserRole.ADMIN || role === UserRole.BANK_TELLER;
};

/**
 * Get user role from stored token
 * Checks localStorage for MSAL access token and extracts roles
 * @returns User role or null if not authenticated
 */
export const getCurrentUserRole = (): UserRole | null => {
    try {
        // MSAL stores tokens in localStorage with keys containing 'accesstoken'
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.includes('accesstoken')) {
                const value = localStorage.getItem(key);
                if (value) {
                    try {
                        const parsed = JSON.parse(value);
                        if (parsed.secret) {
                            // Extract roles from the access token
                            const claims = extractTokenClaims(parsed.secret);
                            if (claims?.roles && Array.isArray(claims.roles)) {
                                // Map Azure AD role names to our UserRole enum
                                // "BankTeller" -> UserRole.BANK_TELLER
                                // "Customer" -> UserRole.USER
                                // "BankAgent" -> UserRole.ADMIN
                                const role = claims.roles[0]; // Use first role
                                
                                if (role === 'BankTeller') {
                                    return UserRole.BANK_TELLER;
                                } else if (role === 'BankAgent') {
                                    return UserRole.ADMIN;
                                } else if (role === 'Customer') {
                                    return UserRole.USER;
                                }
                            }
                        }
                    } catch (e) {
                        // Skip this key if it can't be parsed
                        continue;
                    }
                }
            }
        }

        return null;
    } catch (error) {
        console.error('Error getting current user role:', error);
        return null;
    }
};

/**
 * Get display name for a role
 * @param role User role
 * @returns Human-readable role name
 */
export const getRoleDisplayName = (role: UserRole): string => {
    const displayNames: Record<UserRole, string> = {
        [UserRole.ADMIN]: 'Administrator',
        [UserRole.BANK_TELLER]: 'Bank Teller',
        [UserRole.USER]: 'User'
    };
    return displayNames[role];
};
