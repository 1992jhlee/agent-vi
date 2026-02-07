import { notFound } from "next/navigation";
import { getCompany, getFinancials } from "@/lib/api";
import CompanyDetailClient from "@/components/companies/CompanyDetailClient";

interface Props {
  params: Promise<{ stock_code: string }>;
}

export default async function CompanyDetailPage({ params }: Props) {
  const { stock_code } = await params;

  try {
    const company = await getCompany(stock_code);
    const initialFinancialData = await getFinancials(stock_code, 6);

    return <CompanyDetailClient company={company} stockCode={stock_code} initialData={initialFinancialData} />;
  } catch (e) {
    notFound();
  }
}
