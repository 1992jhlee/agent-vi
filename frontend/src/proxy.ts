import { auth } from "@/auth";

export default auth((req) => {
  if (new URL(req.url).pathname.startsWith("/admin") && !req.auth) {
    return Response.redirect(new URL("/", req.url));
  }
});

export const config = {
  matcher: ["/admin/:path*"],
};
