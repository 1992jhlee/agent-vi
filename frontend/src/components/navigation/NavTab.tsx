"use client";

import Link from "next/link";

interface NavTabProps {
  href: string;
  active: boolean;
  children: React.ReactNode;
}

export default function NavTab({ href, active, children }: NavTabProps) {
  return (
    <Link
      href={href}
      className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
        active
          ? "bg-blue-600 text-white shadow-sm"
          : "bg-gray-100 text-gray-700 hover:bg-gray-200"
      }`}
      aria-current={active ? "page" : undefined}
    >
      {children}
    </Link>
  );
}
