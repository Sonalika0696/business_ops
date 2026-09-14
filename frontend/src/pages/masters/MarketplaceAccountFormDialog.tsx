import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { fulfillmentTypeLabels, marketplaceCodeLabels } from "@/lib/labels";
import { useCreateMarketplaceAccount, useMarketplaces } from "@/api/marketplaceAccounts";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/api/client";
import type { FulfillmentType, MarketplaceCode } from "@/api/types";

const schema = z.object({
  marketplace_code: z.string().min(1, "Choose a marketplace"),
  merchant_id_on_platform: z.string().min(1, "Merchant / seller ID is required"),
  warehouse_pincode: z.string().optional(),
  fulfillment_type: z.string().min(1, "Choose a fulfillment type"),
});
type FormValues = z.infer<typeof schema>;

export function MarketplaceAccountFormDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { push } = useToast();
  const marketplacesQuery = useMarketplaces();
  const createAccount = useCreateMarketplaceAccount();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (open) reset({ marketplace_code: "", merchant_id_on_platform: "", warehouse_pincode: "", fulfillment_type: "" });
  }, [open, reset]);

  const onSubmit = async (values: FormValues) => {
    try {
      await createAccount.mutateAsync({
        marketplace_code: values.marketplace_code as MarketplaceCode,
        merchant_id_on_platform: values.merchant_id_on_platform,
        warehouse_pincode: values.warehouse_pincode || null,
        fulfillment_type: values.fulfillment_type as FulfillmentType,
      });
      push("Marketplace account added.");
      onClose();
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
    <Dialog
      open={open}
      onClose={onClose}
      title="Add marketplace account"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>
            Add account
          </Button>
        </>
      }
    >
      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <Select label="Marketplace" required error={errors.marketplace_code?.message} {...register("marketplace_code")}>
          <option value="">Select…</option>
          {marketplacesQuery.data?.items.map((m) => (
            <option key={m.id} value={m.code}>
              {marketplaceCodeLabels[m.code] ?? m.display_name}
            </option>
          ))}
        </Select>
        <Input
          label="Merchant / seller ID on platform"
          required
          error={errors.merchant_id_on_platform?.message}
          {...register("merchant_id_on_platform")}
        />
        <Select label="Fulfillment type" required error={errors.fulfillment_type?.message} {...register("fulfillment_type")}>
          <option value="">Select…</option>
          {Object.entries(fulfillmentTypeLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Input
          label="Warehouse pincode"
          error={errors.warehouse_pincode?.message}
          {...register("warehouse_pincode")}
        />
      </form>
    </Dialog>
  );
}
