import { useNavigate } from "react-router-dom";
import type { WalletResponse } from "../api/wallets";
import { formatAmount, currencyIcon } from "../utils/format";

interface Props {
  wallet: WalletResponse;
  userId: string;
}

export default function WalletCard({ wallet, userId }: Props) {
  const navigate = useNavigate();

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <span className="text-2xl">{currencyIcon(wallet.currency)}</span>
        <span className="text-xs font-medium bg-gray-100 text-gray-500 px-2 py-1 rounded-full">
          {wallet.currency}
        </span>
      </div>

      <div>
        <p className="text-2xl font-bold text-gray-900">
          {formatAmount(wallet.balance, wallet.currency)}
        </p>
        <p className="text-xs text-gray-400 mt-1">···{wallet.id.slice(-4)}</p>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() =>
            navigate(`/transfer?from=${wallet.id}&userId=${userId}`)
          }
          className="flex-1 bg-blue-600 text-white text-sm rounded-lg py-2 hover:bg-blue-700 transition-colors font-medium"
        >
          Send
        </button>
        <button
          onClick={() =>
            navigate(`/wallets/${wallet.id}/transactions`)
          }
          className="flex-1 border border-gray-300 text-gray-700 text-sm rounded-lg py-2 hover:bg-gray-50 transition-colors font-medium"
        >
          History
        </button>
      </div>
    </div>
  );
}
