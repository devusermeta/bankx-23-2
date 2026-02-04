import React from 'react';
import { AlertCircle } from 'lucide-react';
import { ConfirmationButtons } from '../ConfirmationButtons';
import styles from './ConfirmationDialog.module.css';

export interface ConfirmationDialogProps {
    isOpen: boolean;
    title: string;
    message: string;
    details?: Array<{ label: string; value: string }>;
    confirmationType: 'payment' | 'ticket' | 'email' | 'beneficiary' | 'general';
    onConfirm: () => void;
    onCancel: () => void;
    confirmText?: string;
    cancelText?: string;
}

export const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({
    isOpen,
    title,
    message,
    details,
    confirmationType,
    onConfirm,
    onCancel,
    confirmText = 'Confirm',
    cancelText = 'Cancel'
}) => {
    if (!isOpen) return null;

    const getIconColor = () => {
        switch (confirmationType) {
            case 'payment':
                return '#f59e0b'; // Amber for payments
            case 'ticket':
                return '#3b82f6'; // Blue for tickets
            case 'email':
                return '#8b5cf6'; // Purple for emails
            default:
                return '#6b7280'; // Gray for general
        }
    };

    return (
        <>
            <div className={styles.overlay} onClick={onCancel} />
            <div className={styles.dialog}>
                <div className={styles.header}>
                    <AlertCircle 
                        size={32} 
                        color={getIconColor()} 
                        strokeWidth={2.5}
                    />
                    <h2 className={styles.title}>{title}</h2>
                </div>

                <div className={styles.content}>
                    <p className={styles.message}>{message}</p>

                    {details && details.length > 0 && (
                        <div className={styles.detailsContainer}>
                            {details.map((detail, index) => (
                                <div key={index} className={styles.detailRow}>
                                    <span className={styles.detailLabel}>{detail.label}:</span>
                                    <span className={styles.detailValue}>{detail.value}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className={styles.footer}>
                    <ConfirmationButtons
                        onConfirm={onConfirm}
                        onCancel={onCancel}
                        confirmText={confirmText}
                        cancelText={cancelText}
                    />
                </div>
            </div>
        </>
    );
};
