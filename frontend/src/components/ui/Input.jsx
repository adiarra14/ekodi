import './Input.css';

export default function Input({ label, error, icon, className = '', ...props }) {
  return (
    <div className={`input-group ${error ? 'input-error' : ''} ${className}`}>
      {label && <label className="input-label">{label}</label>}
      <div className="input-wrapper">
        {icon && <span className="input-icon">{icon}</span>}
        <input className="input-field" {...props} />
      </div>
      {error && <span className="input-error-text">{error}</span>}
    </div>
  );
}
