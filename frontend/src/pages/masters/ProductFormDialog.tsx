import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { gstRateOptions } from "@/lib/labels";
import { paiseToRupeesInput, rupeesInputToPaise } from "@/lib/money";
import { useCreateProduct, useUpdateProduct } from "@/api/products";
import { ApiError } from "@/api/client";
import { useToast } from "@/components/ui/Toast";
import type { ProductRead } from "@/api/types";

const schema = z.object({
  internal_sku: z.string().min(1, "SKU is required"),
  product_name: z.string().min(1, "Product name is required"),
  hsn_code: z.string().optional(),
  category_primary: z.string().optional(),
  category_sub: z.string().optional(),
  weight_grams: z.string().optional(),
  mrp: z.string().min(1, "MRP is required"),
  cost_price: z.string().min(1, "Cost price is required"),
  gst_rate: z.string().min(1, "GST rate is required"),
});
type FormValues = z.infer<typeof schema>;

export function ProductFormDialog({
  open,
  onClose,
  product,
}: {
  open: boolean;
  onClose: () => void;
  product: ProductRead | null;
}) {
  const { push } = useToast();
  const createProduct = useCreateProduct();
  const updateProduct = useUpdateProduct(product?.id ?? "");
  const isEdit = Boolean(product);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (open) {
      reset({
        internal_sku: product?.internal_sku ?? "",
        product_name: product?.product_name ?? "",
        hsn_code: product?.hsn_code ?? "",
        category_primary: product?.category_primary ?? "",
        category_sub: product?.category_sub ?? "",
        weight_grams: product?.weight_grams?.toString() ?? "",
        mrp: paiseToRupeesInput(product?.mrp_paise),
        cost_price: paiseToRupeesInput(product?.cost_price_paise),
        gst_rate: product?.gst_rate?.toString() ?? "",
      });
    }
  }, [open, product, reset]);

  const onSubmit = async (values: FormValues) => {
    const payload = {
      internal_sku: values.internal_sku,
      product_name: values.product_name,
      hsn_code: values.hsn_code || null,
      category_primary: values.category_primary || null,
      category_sub: values.category_sub || null,
      weight_grams: values.weight_grams ? Number.parseInt(values.weight_grams, 10) : null,
      mrp_paise: rupeesInputToPaise(values.mrp),
      cost_price_paise: rupeesInputToPaise(values.cost_price),
      gst_rate: Number.parseInt(values.gst_rate, 10),
    };
    try {
      if (isEdit) {
        await updateProduct.mutateAsync(payload);
        push("Product updated.");
      } else {
        await createProduct.mutateAsync(payload);
        push("Product created.");
      }
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
      title={isEdit ? "Edit product" : "Add product"}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit(onSubmit)} loading={isSubmitting}>
            {isEdit ? "Save changes" : "Create product"}
          </Button>
        </>
      }
    >
      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="grid grid-cols-2 gap-4">
          <Input label="Internal SKU" required error={errors.internal_sku?.message} {...register("internal_sku")} />
          <Select label="GST rate" required error={errors.gst_rate?.message} {...register("gst_rate")}>
            <option value="">Select…</option>
            {gstRateOptions.map((rate) => (
              <option key={rate} value={rate}>
                {rate}%
              </option>
            ))}
          </Select>
        </div>
        <Input label="Product name" required error={errors.product_name?.message} {...register("product_name")} />
        <div className="grid grid-cols-2 gap-4">
          <Input label="MRP (₹)" type="number" step="0.01" min="0" required error={errors.mrp?.message} {...register("mrp")} />
          <Input
            label="Cost price (₹)"
            type="number"
            step="0.01"
            min="0"
            required
            error={errors.cost_price?.message}
            {...register("cost_price")}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Input label="Category" error={errors.category_primary?.message} {...register("category_primary")} />
          <Input label="Sub-category" error={errors.category_sub?.message} {...register("category_sub")} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Input label="HSN code" error={errors.hsn_code?.message} {...register("hsn_code")} />
          <Input
            label="Weight (grams)"
            type="number"
            min="0"
            error={errors.weight_grams?.message}
            {...register("weight_grams")}
          />
        </div>
      </form>
    </Dialog>
  );
}
