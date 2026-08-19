/**
 * Tensioned Signal Web: the generated glyph is a compact evidence-web mark, shown clearly rather than as decorative chrome.
 */
export function AegisMark({ size = 42 }: { size?: number }) {
  return (
    <svg className="aegis-mark" style={{ width: size, height: size }} viewBox="0 0 48 48" aria-hidden="true">
      <path d="M24 3 L42 15 L38 37 L24 45 L10 37 L6 15 Z" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M11 16 L24 24 L37 15 M10 36 L24 24 L38 36 M24 3 L24 24" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="24" cy="24" r="4.2" fill="#F3F0E8" /><circle cx="11" cy="16" r="2" fill="#2F7DFF" /><circle cx="38" cy="36" r="2" fill="#F02D42" />
    </svg>
  );
}
