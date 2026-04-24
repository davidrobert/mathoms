import { notFound } from "next/navigation";
import { UiDevPlayground } from "./UiDevPlayground";

export const metadata = { title: "UI primitives dev playground" };

export default function UiDevPage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }
  return <UiDevPlayground />;
}
