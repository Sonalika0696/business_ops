import { NavLink, Outlet } from "react-router-dom";
import { motion } from "framer-motion";
import {
  UploadCloud,
  History,
  PackageSearch,
  Building2,
  Store,
  LogOut,
  ScrollText,
  Scale,
  Undo2,
  Landmark,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { useAuth } from "@/context/AuthContext";
import { useSeller } from "@/api/sellers";

const navItems = [
  { to: "/reconciliation", label: "Reconciliation", icon: Scale },
  { to: "/upload", label: "Upload settlement", icon: UploadCloud },
  { to: "/settlements", label: "Settlement history", icon: History },
  { to: "/returns", label: "Un-credited refunds", icon: Undo2 },
  { to: "/tax", label: "TCS & TDS", icon: Landmark },
  { to: "/products", label: "Products", icon: PackageSearch },
  { to: "/marketplace-accounts", label: "Marketplace accounts", icon: Store },
  { to: "/seller-profile", label: "Seller profile", icon: Building2 },
];

export function AppShell() {
  const { logout } = useAuth();
  const { data: seller } = useSeller();

  return (
    <div className="flex min-h-dvh flex-col bg-background lg:flex-row">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      <aside className="flex shrink-0 flex-col border-b border-border bg-surface lg:h-dvh lg:w-64 lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="flex size-9 items-center justify-center rounded bg-primary text-primary-foreground">
            <ScrollText className="size-5" aria-hidden />
          </div>
          <span className="font-heading text-lg font-semibold text-foreground">Reconcile</span>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 pb-4" aria-label="Primary">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "relative flex items-center gap-3 rounded px-3 py-2.5 text-base font-medium transition-colors duration-150",
                  isActive ? "text-primary-700" : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-pill"
                      className="absolute inset-0 rounded bg-primary-50"
                      transition={{ type: "spring", stiffness: 500, damping: 40 }}
                    />
                  )}
                  <Icon className="relative z-10 size-5 shrink-0" aria-hidden />
                  <span className="relative z-10">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border px-3 py-3.5">
          <div className="flex items-center gap-2.5 rounded px-2.5 py-2">
            <div
              className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-700"
              aria-hidden
            >
              {seller?.legal_name?.[0]?.toUpperCase() ?? "?"}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">{seller?.legal_name ?? "Loading…"}</p>
              <p className="truncate text-xs text-muted-foreground">{seller?.email}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            className="mt-1 flex w-full cursor-pointer items-center gap-3 rounded px-3 py-2.5 text-base font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <LogOut className="size-5" aria-hidden />
            Log out
          </button>
        </div>
      </aside>

      <main id="main-content" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mx-auto max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
