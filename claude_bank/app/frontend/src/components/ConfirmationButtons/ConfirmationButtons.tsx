import React from 'react';
import { Check, X } from 'lucide-react';
import styles from './ConfirmationButtons.module.css';

interface ConfirmationButtonsProps {
    onConfirm: () => void;
    onCancel: () => void;
    confirmText?: string;
    cancelText?: string;
    disabled?: boolean;
}

export const ConfirmationButtons: React.FC<ConfirmationButtonsProps> = ({
    onConfirm,
    onCancel,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    disabled = false
}) => {
    return (
        <div className={styles.buttonContainer}>
            <button
                className={`${styles.button} ${styles.confirmButton}`}
                onClick={onConfirm}
                disabled={disabled}
                aria-label={confirmText}
                title={confirmText}
            >
                <Check className={styles.icon} size={20} strokeWidth={3} />
                <span className={styles.buttonText}>{confirmText}</span>
            </button>
            
            <button
                className={`${styles.button} ${styles.cancelButton}`}
                onClick={onCancel}
                disabled={disabled}
                aria-label={cancelText}
                title={cancelText}
            >
                <X className={styles.icon} size={20} strokeWidth={3} />
                <span className={styles.buttonText}>{cancelText}</span>
            </button>
        </div>
    );
};
