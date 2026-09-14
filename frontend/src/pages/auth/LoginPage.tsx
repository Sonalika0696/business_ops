import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ScrollText, LogIn } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { login as loginRequest } from "@/api/auth";
import { ApiError } from "@/api/client";

const schema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (isAuthenticated) {
    const from = (location.state as { from?: Location })?.from?.pathname ?? "/upload";
    return <Navigate to={from} replace />;
  }

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    setSubmitting(true);
    try {
      const { access_token } = await loginRequest(values);
      login(access_token);
      navigate("/upload", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 404)) {
        setFormError("That email and password combination doesn't match our records.");
      } else if (err instanceof ApiError) {
        setFormError(err.message);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex size-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ScrollText className="size-6" aria-hidden />
          </div>
          <div>
            <h1 className="font-heading text-2xl font-semibold text-foreground">Sign in to Reconcile</h1>
            <p className="mt-1 text-base text-muted-foreground">Marketplace settlement reconciliation</p>
          </div>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4 rounded-md border border-border bg-surface p-6 shadow-card"
          noValidate
        >
          {formError && (
            <div className="rounded border border-danger/20 bg-danger-soft px-3.5 py-2.5 text-sm text-danger" role="alert">
              {formError}
            </div>
          )}
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            error={errors.email?.message}
            {...register("email")}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            error={errors.password?.message}
            {...register("password")}
          />
          <Button type="submit" size="lg" loading={submitting} icon={<LogIn className="size-4" aria-hidden />} className="mt-1">
            Sign in
          </Button>
        </form>

        <p className="mt-5 text-center text-base text-muted-foreground">
          New here?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
