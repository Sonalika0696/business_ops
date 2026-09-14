import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getReturnsQueue, setReturnClaimStatus } from "./fixtureData";

const MOCK_DELAY_MS = 350;
const delay = <T,>(value: T) => new Promise<T>((resolve) => setTimeout(() => resolve(value), MOCK_DELAY_MS));
const key = ["mock", "returns-queue"] as const;

export function useReturnsQueue() {
  return useQuery({ queryKey: key, queryFn: () => delay(getReturnsQueue()) });
}

export function useFileClaim() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id }: { id: string }) => {
      setReturnClaimStatus(id, "CLAIMED");
      return delay({ id });
    },
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
}
