import type { Metadata } from "next"
import { CreateTwinFlow } from "@/features/create/CreateTwinFlow"

export const metadata: Metadata = {
  title: "Create your digital twin — DreamTalk",
  description:
    "Build your visual and vocal identity: introduce your face and voice, choose your languages, and generate an interactive digital human.",
}

export default function CreateTwinPage() {
  return <CreateTwinFlow />
}
