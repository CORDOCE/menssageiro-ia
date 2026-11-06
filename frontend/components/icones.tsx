// Ícones em SVG inline (traço) — sem biblioteca (ADR 0010).
import type { SVGProps } from "react";

type Props = SVGProps<SVGSVGElement>;

function base(props: Props) {
  return {
    width: 20,
    height: 20,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className: "icone",
    "aria-hidden": true,
    ...props,
  };
}

export function IconeHoje(props: Props) {
  return (
    <svg {...base(props)}>
      <path d="M3 9.5 12 3l9 6.5" />
      <path d="M5 10v10h14V10" />
    </svg>
  );
}

export function IconeContatos(props: Props) {
  return (
    <svg {...base(props)}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20c0-3 2.5-5 6-5s6 2 6 5" />
      <path d="M16 3.5a3 3 0 0 1 0 6M21 20c0-2.5-1.5-4.2-4-4.8" />
    </svg>
  );
}

export function IconeAgenda(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="3" y="4" width="18" height="17" rx="2" />
      <path d="M3 9h18M8 2v4M16 2v4" />
    </svg>
  );
}

export function IconeModelos(props: Props) {
  return (
    <svg {...base(props)}>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M9 8h6M9 12h6M9 16h4" />
    </svg>
  );
}

export function IconeRecorrencia(props: Props) {
  return (
    <svg {...base({ width: 16, height: 16, ...props })}>
      <path d="M4 10a8 8 0 0 1 13-3l3 3" />
      <path d="M20 4v6h-6" />
      <path d="M20 14a8 8 0 0 1-13 3l-3-3" />
      <path d="M4 20v-6h6" />
    </svg>
  );
}

export function IconeSol(props: Props) {
  return (
    <svg {...base({ width: 18, height: 18, ...props })}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" />
    </svg>
  );
}

export function IconeLua(props: Props) {
  return (
    <svg {...base({ width: 18, height: 18, ...props })}>
      <path d="M21 12.8A8 8 0 1 1 11.2 3a6 6 0 0 0 9.8 9.8Z" />
    </svg>
  );
}

export function IconeSistema(props: Props) {
  return (
    <svg {...base({ width: 18, height: 18, ...props })}>
      <rect x="3" y="4" width="18" height="12" rx="1" />
      <path d="M8 20h8M12 16v4" />
    </svg>
  );
}

export function IconeCadeado(props: Props) {
  return (
    <svg {...base({ width: 16, height: 16, ...props })}>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}
