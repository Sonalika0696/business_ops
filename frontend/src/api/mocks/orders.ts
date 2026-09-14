import { useQuery } from "@tanstack/react-query";
import { getOrderDetail } from "./fixtureData";

const MOCK_DELAY_MS = 300;
const delay = <T,>(value: T) => new Promise<T>((resolve) => setTimeout(() => resolve(value), MOCK_DELAY_MS));

export function useOrderDetail(orderId: string | undefined) {
  return useQuery({
    queryKey: ["mock", "order-detail", orderId],
    queryFn: () => delay(getOrderDetail(orderId!)),
    enabled: Boolean(orderId),
  });
}
