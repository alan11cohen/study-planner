import { Navigate } from "react-router-dom";
import { getTokenPayload } from "../../api/client";

interface Props {
  children: React.ReactNode;
}

export default function PrivateRoute({ children }: Props) {
  const payload = getTokenPayload();
  if (!payload) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
