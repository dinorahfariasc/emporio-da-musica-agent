import { Suspense } from "react";

import { LoginForm } from "@/components/login/login-form";
import { LoginScreen } from "@/components/login/login-screen";

export default function LoginPage() {
  return (
    <LoginScreen>
      {/* useSearchParams needs a Suspense boundary under Cache Components. */}
      <Suspense>
        <LoginForm />
      </Suspense>
    </LoginScreen>
  );
}
