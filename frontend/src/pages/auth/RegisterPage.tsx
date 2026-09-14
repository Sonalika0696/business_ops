import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ScrollText, UserPlus } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { register as registerRequest, login as loginRequest } from "@/api/auth";
import { ApiError } from "@/api/client";

const schema = z.object({
  legal_name: z.string().min(1, "Business / legal name is required"),
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
type FormValues = z.infer<typeof schema>;

export function RegisterPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register: registerField,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (isAuthenticated) return <Navigate to="/upload" replace />;

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    setSubmitting(true);
    try {
      await registerRequest(values);
      const { access_token } = await loginRequest({ email: values.email, password: values.password });
      login(access_token);
      navigate("/upload", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        for (const [field, message] of Object.entries(err.fieldErrors)) {
          if (field in ({} as FormValues) || ["legal_name", "email", "password"].includes(field)) {
            setError(field as keyof FormValues, { message });
          }
        }
        setFormError(err.message);
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
            <h1 className="font-heading text-2xl font-semibold text-foreground">Create your account</h1>
            <p className="mt-1 text-base text-muted-foreground">Start reconciling your settlements</p>
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
            label="Business / legal name"
            autoComplete="organization"
            required
            error={errors.legal_name?.message}
            {...registerField("legal_name")}
          />
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            error={errors.email?.message}
            {...registerField("email")}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="new-password"
            required
            helperText={!errors.password ? "At least 8 characters" : undefined}
            error={errors.password?.message}
            {...registerField("password")}
          />
          <Button type="submit" size="lg" loading={submitting} icon={<UserPlus className="size-4" aria-hidden />} className="mt-1">
            Create account
          </Button>
        </form>

        <p className="mt-5 text-center text-base text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
