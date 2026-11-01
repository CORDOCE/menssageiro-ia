"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { lerToken } from "@/lib/auth";

// Raiz: encaminha para o painel (se já tem token) ou para o login.
export default function Home(): null {
  const router = useRouter();
  useEffect(() => {
    router.replace(lerToken() ? "/painel" : "/login");
  }, [router]);
  return null;
}
