import './Button.css';

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  loading,
  className = '',
  ...props
}) {
  return (
    <button
      className={`btn btn-${variant} btn-${size} ${loading ? 'btn-loading' : ''} ${className}`}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && <span className="btn-spinner" />}
      {icon && !loading && <span className="btn-icon">{icon}</span>}
      {children}
    </button>
  );
}
