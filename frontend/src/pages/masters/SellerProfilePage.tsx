import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Save, Wand2 } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { AsyncState } from "@/components/ui/AsyncState";
import { VerificationHint } from "@/components/masters/VerificationHint";
import { useSeller, useUpdateSeller } from "@/api/sellers";
import { msmeClassificationLabels } from "@/lib/labels";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/api/client";
import { validateGSTIN, validateIFSC, validatePAN, validateUdyam, lookupPincode } from "@/lib/verification";
import type { MsmeClassification } from "@/api/types";

const schema = z.object({
  legal_name: z.string().min(1, "Legal name is required"),
  trade_name: z.string().optional(),
  gstin: z.string().optional(),
  pan: z.string().optional(),
  udyam_registration_number: z.string().optional(),
  msme_classification: z.string(),
  primary_state: z.string().optional(),
  primary_pincode: z.string().optional(),
  principal_place_of_business: z.string().optional(),
  bank_account_number: z.string().optional(),
  bank_ifsc: z.string().optional(),
  bank_name: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function SellerProfilePage() {
  const sellerQuery = useSeller();
  const updateSeller = useUpdateSeller();
  const { push } = useToast();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    setValue,
    watch,
    formState: { errors, isDirty },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const [gstinValue, panValue, udyamValue, pincodeValue, ifscValue, bankNameValue, primaryStateValue] = watch([
    "gstin",
    "pan",
    "udyam_registration_number",
    "primary_pincode",
    "bank_ifsc",
    "bank_name",
    "primary_state",
  ]);

  const gstinResult = useMemo(() => (gstinValue ? validateGSTIN(gstinValue) : null), [gstinValue]);
  const panResult = useMemo(() => (panValue ? validatePAN(panValue) : null), [panValue]);
  const udyamResult = useMemo(() => (udyamValue ? validateUdyam(udyamValue) : null), [udyamValue]);
  const pincodeResult = useMemo(() => (pincodeValue ? lookupPincode(pincodeValue) : null), [pincodeValue]);
  const ifscResult = useMemo(() => (ifscValue ? validateIFSC(ifscValue) : null), [ifscValue]);

  useEffect(() => {
    const seller = sellerQuery.data;
    if (seller) {
      reset({
        legal_name: seller.legal_name,
        trade_name: seller.trade_name ?? "",
        gstin: seller.gstin ?? "",
        pan: seller.pan ?? "",
        udyam_registration_number: seller.udyam_registration_number ?? "",
        msme_classification: seller.msme_classification,
        primary_state: seller.primary_state ?? "",
        primary_pincode: seller.primary_pincode ?? "",
        principal_place_of_business: seller.principal_place_of_business ?? "",
        bank_account_number: seller.bank_account_number ?? "",
        bank_ifsc: seller.bank_ifsc ?? "",
        bank_name: seller.bank_name ?? "",
      });
    }
  }, [sellerQuery.data, reset]);

  const onSubmit = async (values: FormValues) => {
    try {
      await updateSeller.mutateAsync({
        legal_name: values.legal_name,
        trade_name: values.trade_name || null,
        gstin: values.gstin || null,
        pan: values.pan || null,
        udyam_registration_number: values.udyam_registration_number || null,
        msme_classification: values.msme_classification as MsmeClassification,
        primary_state: values.primary_state || null,
        primary_pincode: values.primary_pincode || null,
        principal_place_of_business: values.principal_place_of_business || null,
        bank_account_number: values.bank_account_number || null,
        bank_ifsc: values.bank_ifsc || null,
        bank_name: values.bank_name || null,
      });
      push("Profile updated.");
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        for (const [field, message] of Object.entries(err.fieldErrors)) {
          if (field in schema.shape) setError(field as keyof FormValues, { message });
        }
      } else if (err instanceof ApiError) {
        push(err.message, "danger");
      }
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-foreground">Seller profile</h1>
        <p className="mt-1 text-base text-muted-foreground">Your business details, used across compliance and payouts.</p>
      </div>

      <AsyncState
        isLoading={sellerQuery.isLoading}
        isError={sellerQuery.isError}
        error={sellerQuery.error}
        onRetry={() => sellerQuery.refetch()}
      >
        {sellerQuery.data && (
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Business identity</CardTitle>
              </CardHeader>
              <CardBody className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input label="Legal name" required error={errors.legal_name?.message} {...register("legal_name")} />
                <Input label="Trade name" error={errors.trade_name?.message} {...register("trade_name")} />
                <Input
                  label="Email"
                  value={sellerQuery.data.email}
                  readOnly
                  disabled
                  helperText="Contact support to change your login email"
                />
                <Select
                  label="MSME classification"
                  error={errors.msme_classification?.message}
                  {...register("msme_classification")}
                >
                  {Object.entries(msmeClassificationLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
                <div>
                  <Input label="GSTIN" error={errors.gstin?.message} {...register("gstin")} />
                  <VerificationHint
                    result={gstinResult}
                    action={
                      gstinResult?.valid && gstinResult.stateName && !primaryStateValue ? (
                        <button
                          type="button"
                          onClick={() => setValue("primary_state", gstinResult.stateName!, { shouldDirty: true })}
                          className="cursor-pointer font-medium underline hover:no-underline"
                        >
                          Use as primary state
                        </button>
                      ) : undefined
                    }
                  />
                </div>
                <div>
                  <Input label="PAN" error={errors.pan?.message} {...register("pan")} />
                  <VerificationHint result={panResult} />
                </div>
                <div>
                  <Input
                    label="Udyam registration number"
                    error={errors.udyam_registration_number?.message}
                    {...register("udyam_registration_number")}
                  />
                  <VerificationHint result={udyamResult} />
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Location</CardTitle>
              </CardHeader>
              <CardBody className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input label="Primary state" error={errors.primary_state?.message} {...register("primary_state")} />
                <div>
                  <Input label="Primary pincode" error={errors.primary_pincode?.message} {...register("primary_pincode")} />
                  <VerificationHint
                    result={pincodeResult}
                    action={
                      pincodeResult?.valid && pincodeResult.stateGuess && !primaryStateValue ? (
                        <button
                          type="button"
                          onClick={() => setValue("primary_state", pincodeResult.stateGuess!, { shouldDirty: true })}
                          className="cursor-pointer font-medium underline hover:no-underline"
                        >
                          Use as primary state
                        </button>
                      ) : undefined
                    }
                  />
                </div>
                <Input
                  label="Principal place of business"
                  className="sm:col-span-2"
                  error={errors.principal_place_of_business?.message}
                  {...register("principal_place_of_business")}
                />
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Bank details</CardTitle>
              </CardHeader>
              <CardBody className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input label="Bank name" error={errors.bank_name?.message} {...register("bank_name")} />
                <div>
                  <Input label="IFSC" error={errors.bank_ifsc?.message} {...register("bank_ifsc")} />
                  <VerificationHint
                    result={ifscResult}
                    action={
                      ifscResult?.valid && ifscResult.bankName && !bankNameValue ? (
                        <button
                          type="button"
                          onClick={() => setValue("bank_name", ifscResult.bankName!, { shouldDirty: true })}
                          className="inline-flex cursor-pointer items-center gap-1 font-medium underline hover:no-underline"
                        >
                          <Wand2 className="size-3" aria-hidden />
                          Autofill bank name
                        </button>
                      ) : undefined
                    }
                  />
                </div>
                <Input
                  label="Account number"
                  className="sm:col-span-2"
                  error={errors.bank_account_number?.message}
                  {...register("bank_account_number")}
                />
              </CardBody>
            </Card>

            <div>
              <Button type="submit" loading={updateSeller.isPending} disabled={!isDirty} icon={<Save className="size-4" aria-hidden />}>
                Save changes
              </Button>
            </div>
          </form>
        )}
      </AsyncState>
    </div>
  );
}
