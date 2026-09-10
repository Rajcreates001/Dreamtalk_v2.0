"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import {
  User, Shield, Bell, Key, Palette, Users,
  CreditCard, Sliders,
} from "lucide-react"

const SETTINGS_TABS = [
  { id: "account", label: "Account", icon: User },
  { id: "organization", label: "Organization", icon: Users },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "security", label: "Security", icon: Shield },
  { id: "api", label: "API Keys", icon: Key },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "advanced", label: "Advanced", icon: Sliders },
]

const TOGGLE_ITEMS = [
  { label: "Conversation summaries", desc: "Daily digest of AI conversations", default: true },
  { label: "Usage alerts", desc: "When approaching plan limits", default: true },
  { label: "Avatar status", desc: "When avatars go offline or error", default: false },
  { label: "Product updates", desc: "New features and improvements", default: true },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("account")
  const [toggles, setToggles] = useState(TOGGLE_ITEMS.map(t => t.default))

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-[#F8FAFC]">Settings</h1>
        <p className="text-sm text-[#94A3B8] mt-1">Manage your account and workspace</p>
      </div>

      <div className="flex gap-6">
        <div className="w-44 shrink-0 space-y-1">
          {SETTINGS_TABS.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
                  isActive
                    ? "bg-[#7C5CFF]/10 text-[#F8FAFC] border border-[#7C5CFF]/20"
                    : "text-[#94A3B8] hover:text-[#CBD5E1] hover:bg-white/[0.04] border border-transparent"
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </div>

        <div className="flex-1 rounded-xl bg-[#0F172A]/80 border border-white/[0.06] p-6 space-y-6">
          {activeTab === "account" && (
            <div className="space-y-5">
              <h3 className="text-sm font-semibold text-[#F8FAFC]">Account Settings</h3>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-[#94A3B8]">Full Name</label>
                  <input type="text" defaultValue="Alex" className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-[#F8FAFC] focus:outline-none focus:ring-2 focus:ring-[#7C5CFF]/30" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs text-[#94A3B8]">Email</label>
                  <input type="email" defaultValue="alex@dreamtalk.ai" className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-[#F8FAFC] focus:outline-none focus:ring-2 focus:ring-[#7C5CFF]/30" />
                </div>
              </div>
              <button className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white text-sm font-medium">Save Changes</button>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-[#F8FAFC]">Notification Preferences</h3>
              {TOGGLE_ITEMS.map((item, i) => (
                <div key={item.label} className="flex items-center justify-between py-2">
                  <div>
                    <p className="text-sm text-[#CBD5E1]">{item.label}</p>
                    <p className="text-xs text-[#64748B]">{item.desc}</p>
                  </div>
                  <button
                    onClick={() => setToggles(prev => prev.map((v, j) => j === i ? !v : v))}
                    className={cn(
                      "w-9 h-5 rounded-full transition-all relative",
                      toggles[i] ? "bg-[#7C5CFF]" : "bg-white/[0.08]"
                    )}
                  >
                    <div className={cn(
                      "absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all",
                      toggles[i] ? "left-[18px]" : "left-0.5"
                    )} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {activeTab === "security" && (
            <div className="space-y-5">
              <h3 className="text-sm font-semibold text-[#F8FAFC]">Security</h3>
              <div className="space-y-1.5">
                <label className="text-xs text-[#94A3B8]">Current Password</label>
                <input type="password" placeholder="••••••••" className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm focus:outline-none focus:ring-2 focus:ring-[#7C5CFF]/30" />
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-[#94A3B8]">New Password</label>
                  <input type="password" placeholder="New password" className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm focus:outline-none focus:ring-2 focus:ring-[#7C5CFF]/30" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs text-[#94A3B8]">Confirm Password</label>
                  <input type="password" placeholder="Confirm" className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm focus:outline-none focus:ring-2 focus:ring-[#7C5CFF]/30" />
                </div>
              </div>
              <button className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#7C5CFF] to-[#00E5FF] text-white text-sm font-medium">Update Password</button>
            </div>
          )}

          {activeTab === "api" && (
            <div className="space-y-5">
              <h3 className="text-sm font-semibold text-[#F8FAFC]">API Keys</h3>
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-[#94A3B8]">Production Key</span>
                  <span className="text-[10px] text-[#42FFC6]">Active</span>
                </div>
                <code className="text-xs text-[#CBD5E1] font-mono">dt_sk_prod_••••••••••••••••</code>
              </div>
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-[#94A3B8]">Development Key</span>
                  <span className="text-[10px] text-[#FBBF24]">Testing</span>
                </div>
                <code className="text-xs text-[#CBD5E1] font-mono">dt_sk_dev_••••••••••••••••</code>
              </div>
              <button className="px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-sm text-[#94A3B8] hover:text-[#F8FAFC] transition-all">Generate New Key</button>
            </div>
          )}

          {activeTab !== "account" && activeTab !== "notifications" && activeTab !== "security" && activeTab !== "api" && (
            <div className="flex items-center justify-center h-48">
              <p className="text-sm text-[#64748B]">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} settings coming soon</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
