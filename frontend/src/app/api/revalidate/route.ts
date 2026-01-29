import { revalidatePath } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { slug, secret } = body;

  if (secret !== process.env.REVALIDATION_SECRET) {
    return NextResponse.json({ error: "Invalid secret" }, { status: 401 });
  }

  revalidatePath(`/reports/${slug}`);
  revalidatePath("/reports");
  revalidatePath("/");

  return NextResponse.json({ revalidated: true });
}
