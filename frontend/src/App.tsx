import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { queryClient } from "@/api/queryClient";
import { AuthProvider } from "@/context/AuthContext";
import { ToastProvider } from "@/components/ui/Toast";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { UploadPage } from "@/pages/settlements/UploadPage";
import { SettlementsHistoryPage } from "@/pages/settlements/SettlementsHistoryPage";
import { SettlementDetailPage } from "@/pages/settlements/SettlementDetailPage";
import { ProductsPage } from "@/pages/masters/ProductsPage";
import { MarketplaceAccountsPage } from "@/pages/masters/MarketplaceAccountsPage";
import { SellerProfilePage } from "@/pages/masters/SellerProfilePage";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* reducedMotion="user" makes every framer-motion animation in the
          app honor prefers-reduced-motion automatically — our plain-CSS
          rule in styles/index.css only covers CSS transitions/animations,
          not framer-motion's imperative ones. */}
      <MotionConfig reducedMotion="user">
        <BrowserRouter>
          <AuthProvider>
            <ToastProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />

                <Route element={<ProtectedRoute />}>
                  <Route element={<AppShell />}>
                    <Route path="/" element={<Navigate to="/upload" replace />} />
                    <Route path="/upload" element={<UploadPage />} />
                    <Route path="/settlements" element={<SettlementsHistoryPage />} />
                    <Route path="/settlements/:reportId" element={<SettlementDetailPage />} />
                    <Route path="/products" element={<ProductsPage />} />
                    <Route path="/marketplace-accounts" element={<MarketplaceAccountsPage />} />
                    <Route path="/seller-profile" element={<SellerProfilePage />} />
                  </Route>
                </Route>

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ToastProvider>
          </AuthProvider>
        </BrowserRouter>
      </MotionConfig>
    </QueryClientProvider>
  );
}
