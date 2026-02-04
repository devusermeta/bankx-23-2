import React from 'react';
import './styles.css';

interface ConfirmationDetails {
  label: string;
  value: string;
}

interface HumanInLoopConfirmationProps {
  title: string;
  message: string;
  details?: ConfirmationDetails[];
  confirmationType: 'payment' | 'ticket' | 'email' | 'beneficiary' | 'general';
  onConfirm: () => void;
  onCancel: () => void;
  confirmText?: string;
  cancelText?: string;
  isSubmitting?: boolean;
}

const formatKey = (key: string): string =>
  key
    .split(/[_-]/g)
    .map((segment) => (segment ? segment[0].toUpperCase() + segment.slice(1) : segment))
    .join(' ');

const HumanInLoopConfirmation: React.FC<HumanInLoopConfirmationProps> = ({
  title,
  message,
  details,
  confirmationType,
  onConfirm,
  onCancel,
  confirmText = 'Approve',
  cancelText = 'Cancel',
  isSubmitting = false
}) => {
  const hasDetails = details && details.length > 0;

  const handleDecision = (action: 'confirm' | 'cancel') => {
    if (isSubmitting) {
      return;
    }
    if (action === 'confirm') {
      onConfirm();
    } else {
      onCancel();
    }
  };

  // Get icon based on confirmation type
  const getIcon = () => {
    switch (confirmationType) {
      case 'payment':
        return '💳';
      case 'ticket':
        return '🎫';
      case 'email':
        return '✉️';
      case 'beneficiary':
        return '👤';
      default:
        return '⚠️';
    }
  };

  return (
    <div className="human-in-loop-confirmation" data-testid="human-in-loop-confirmation">
      <div className="bubble bubble--agent human-in-loop-confirmation__bubble">
        <div className="human-in-loop-confirmation__meta">
          <div>
            <p className="human-in-loop-confirmation__title">
              <span className="human-in-loop-confirmation__icon">{getIcon()}</span>
              {title}
            </p>
            {message && (
              <p className="human-in-loop-confirmation__subtitle">
                {message}
              </p>
            )}
          </div>
        </div>

        {hasDetails ? (
          <dl className="human-in-loop-confirmation__details">
            {details.map((detail, index) => (
              <div className="human-in-loop-confirmation__detail" key={index}>
                <dt>{formatKey(detail.label)}</dt>
                <dd>{detail.value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="human-in-loop-confirmation__placeholder">No additional details provided.</p>
        )}

        <div className="human-in-loop-confirmation__actions">
          <button
            type="button"
            className="button button--secondary"
            onClick={() => handleDecision('cancel')}
            disabled={isSubmitting}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className="button"
            onClick={() => handleDecision('confirm')}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Submitting...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default HumanInLoopConfirmation;
