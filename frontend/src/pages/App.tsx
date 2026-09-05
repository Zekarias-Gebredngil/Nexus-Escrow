import { CheckCircle2, ShieldCheck, Truck, WalletCards } from "lucide-react";

import { StatusPill } from "../components/StatusPill";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        initData: string;
      };
    };
  }
}

const steps = [
  { label: "Terms", icon: ShieldCheck, done: true },
  { label: "Payment", icon: WalletCards, done: true },
  { label: "Shipping", icon: Truck, done: false },
  { label: "Release", icon: CheckCircle2, done: false }
];

export function App() {
  window.Telegram?.WebApp?.ready();
  window.Telegram?.WebApp?.expand();

  return (
    <main className="app-shell">
      <section className="escrow-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Nexus Escrow</p>
            <h1>iPhone 14 Pro Max</h1>
          </div>
          <StatusPill label="Paid" tone="success" />
        </div>

        <div className="amount-row">
          <span>Total secured</span>
          <strong>3,075.00 ETB</strong>
        </div>

        <div className="step-grid" aria-label="Escrow progress">
          {steps.map((step) => (
            <div className="step" data-done={step.done} key={step.label}>
              <step.icon size={18} aria-hidden />
              <span>{step.label}</span>
            </div>
          ))}
        </div>

        <div className="action-grid">
          <button type="button" className="primary-action">
            <Truck size={18} aria-hidden />
            Submit Tracking
          </button>
          <button type="button" className="secondary-action">
            File Dispute
          </button>
        </div>
      </section>
    </main>
  );
}

