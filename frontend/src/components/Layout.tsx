import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useSession } from "../session";
import { Button } from "./ui";
import { OperatorPanel } from "./OperatorPanel";

export function Layout({ children }: { children: ReactNode }) {
  const { isOperator, signOut, refresh } = useSession();
  const [panelOpen, setPanelOpen] = useState(false);
  const [signInOpen, setSignInOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-line bg-paper/85 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="group flex items-baseline gap-2">
            <span className="font-display text-xl font-semibold tracking-tight text-ink">
              Impact Desk
            </span>
            <span className="text-xs uppercase tracking-[0.2em] text-ink-faint">
              median-first ranking
            </span>
          </Link>

          <div className="flex items-center gap-3">
            {isOperator ? (
              <>
                <span className="hidden text-xs uppercase tracking-wide text-real sm:inline">
                  ● Operator
                </span>
                <Button variant="outline" onClick={() => setPanelOpen(true)}>
                  Tools
                </Button>
                <Button variant="ghost" onClick={signOut}>
                  Sign out
                </Button>
              </>
            ) : (
              <>
                <span className="hidden text-xs uppercase tracking-wide text-ink-faint sm:inline">
                  ○ Client · read only
                </span>
                <Button variant="outline" onClick={() => setSignInOpen(true)}>
                  Operator sign in
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>

      {signInOpen && <SignInDialog onClose={() => setSignInOpen(false)} />}
      {panelOpen && isOperator && (
        <OperatorPanel onClose={() => setPanelOpen(false)} onChanged={refresh} />
      )}
    </div>
  );
}

function SignInDialog({ onClose }: { onClose: () => void }) {
  const { signIn } = useSession();
  const [value, setValue] = useState("");

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-ink/25 p-4" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-lg border border-line bg-paper-raised p-6 shadow-2xl rise"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-display text-lg font-semibold text-ink">Operator sign in</h2>
        <p className="mt-1 text-sm text-ink-soft">
          Enter the operator token to enable pulls, imports and export. Clients browse read-only
          without one.
        </p>
        <input
          autoFocus
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && value && (signIn(value), onClose())}
          placeholder="operator token"
          className="mt-4 w-full rounded-md border border-line-strong bg-paper px-3 py-2 text-sm outline-none focus:border-ink"
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={!value}
            onClick={() => {
              signIn(value);
              onClose();
            }}
          >
            Sign in
          </Button>
        </div>
        <p className="mt-3 text-xs text-ink-faint">Dev token: <code>dev-operator-token</code></p>
      </div>
    </div>
  );
}
