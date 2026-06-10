"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  UploadCloud, 
  FileText, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2, 
  ArrowRight, 
  Search, 
  ArrowLeft, 
  TrendingUp, 
  Wallet, 
  Layers, 
  RefreshCw, 
  Sparkles,
  Info
} from "lucide-react";
import { toast } from "sonner";
import { api, JobDetails, Transaction } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";

// Status pipeline steps mapping
const PIPELINE_STEPS = [
  { id: "upload", label: "Secure File Upload", description: "CSV uploaded and stored safely" },
  { id: "pending", label: "Queue Processing", description: "Registering task with celery worker" },
  { id: "cleansing", label: "Data Cleansing", description: "Validating formats, dates and values" },
  { id: "anomalies", label: "Anomaly Engine", description: "Running Isolation Forest scoring" },
  { id: "narrative", label: "AI Narrative Brief", description: "Synthesizing insights via Gemini" }
];

export default function LandingPage() {
  // Navigation / view states: "upload" | "processing" | "results"
  const [view, setView] = useState<"upload" | "processing" | "results">("upload");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobDetails, setJobDetails] = useState<JobDetails | null>(null);
  const [recentJobs, setRecentJobs] = useState<JobDetails[]>([]);
  const [loadingRecent, setLoadingRecent] = useState(false);
  const [geminiKey, setGeminiKey] = useState<string>("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedKey = localStorage.getItem("user_gemini_key");
      if (savedKey) setGeminiKey(savedKey);
    }
  }, []);
  
  // Drag & drop upload states
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Search & Filter & Pagination states for dashboard
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTab, setActiveTab] = useState<"all" | "anomalies">("all");
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  // Poll timer reference
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch recent jobs on load
  const fetchRecentJobs = async () => {
    setLoadingRecent(true);
    try {
      const jobs = await api.listJobs();
      // Sort: most recent first
      const sorted = [...jobs].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setRecentJobs(sorted);
    } catch (error: any) {
      console.error("Failed to list jobs", error);
    } finally {
      setLoadingRecent(false);
    }
  };

  useEffect(() => {
    fetchRecentJobs();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Poll job status
  const startPolling = (jobId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    
    setView("processing");
    setActiveJobId(jobId);
    
    pollIntervalRef.current = setInterval(async () => {
      try {
        const details = await api.getJobStatus(jobId);
        setJobDetails(details);
        
        if (details.status === "completed") {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          toast.success("Transaction intelligence processing completed!");
          
          // Fetch full results including transactions
          const results = await api.getJobResults(jobId);
          setJobDetails(results);
          setView("results");
          fetchRecentJobs();
        } else if (details.status === "failed") {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          toast.error(`Processing failed: ${details.error_message || "Unknown error"}`);
          setView("upload");
          fetchRecentJobs();
        }
      } catch (error: any) {
        console.error("Polling error:", error);
        toast.error("Error updating job progress status.");
      }
    }, 1500);
  };

  // Handle file selection & upload
  const handleFileUpload = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      toast.error("Please upload a valid CSV file.");
      return;
    }
    
    setIsUploading(true);
    const toastId = toast.loading("Uploading transaction statement CSV...");
    
    try {
      const response = await api.uploadCSV(file, geminiKey);
      toast.dismiss(toastId);
      toast.success("File uploaded successfully! Initializing pipeline...");
      
      // Start polling for this new job
      startPolling(response.job_id);
    } catch (error: any) {
      toast.dismiss(toastId);
      toast.error(error.message || "Failed to upload file.");
      console.error(error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileUpload(file);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  };

  // Helper: compute active step index for linear progress & status checks
  const getPipelineProgress = () => {
    if (!jobDetails) return 20; // Default upload done
    switch (jobDetails.status) {
      case "pending":
        return 40;
      case "processing":
        // Check dynamic cues
        if (jobDetails.row_count_clean && jobDetails.row_count_clean > 0) {
          return 75; // cleansing and anomaly done, llm narrative left
        }
        return 60; // cleansing active
      case "completed":
        return 100;
      case "failed":
      default:
        return 0;
    }
  };

  const getStepStatus = (stepId: string) => {
    if (!jobDetails) {
      return stepId === "upload" ? "active" : "upcoming";
    }

    const currentStatus = jobDetails.status;
    const progress = getPipelineProgress();

    if (currentStatus === "completed") return "completed";
    if (currentStatus === "failed") return "failed";

    if (stepId === "upload") return "completed";
    
    if (stepId === "pending") {
      if (currentStatus === "pending") return "active";
      if (currentStatus === "processing") return "completed";
    }

    if (stepId === "cleansing") {
      if (currentStatus === "pending") return "upcoming";
      if (currentStatus === "processing") {
        if (progress > 60) return "completed";
        return "active";
      }
    }

    if (stepId === "anomalies") {
      if (currentStatus === "pending") return "upcoming";
      if (currentStatus === "processing") {
        if (progress > 70) return "completed";
        if (progress === 60) return "upcoming";
        return "active";
      }
    }

    if (stepId === "narrative") {
      if (currentStatus === "processing" && progress >= 75) return "active";
      return "upcoming";
    }

    return "upcoming";
  };

  // Helper currency formatters
  const formatINR = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(val);
  };

  const formatUSD = (val: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2
    }).format(val);
  };

  const getRiskColor = (level?: string) => {
    const l = level?.toLowerCase();
    if (l === "high") return "bg-red-500/10 text-red-400 border-red-500/20";
    if (l === "medium") return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
    return "bg-green-500/10 text-green-400 border-green-500/20";
  };

  // Filter transaction list
  const getFilteredTransactions = () => {
    if (!jobDetails || !jobDetails.transactions) return [];
    
    let list = jobDetails.transactions;
    
    if (activeTab === "anomalies") {
      list = list.filter(t => t.is_anomaly);
    }
    
    if (searchTerm.trim() !== "") {
      const q = searchTerm.toLowerCase();
      list = list.filter(
        t => 
          (t.merchant?.toLowerCase() || "").includes(q) ||
          (t.category?.toLowerCase() || "").includes(q) ||
          (t.txn_id?.toLowerCase() || "").includes(q) ||
          (t.anomaly_reason?.toLowerCase() || "").includes(q)
      );
    }
    
    return list;
  };

  // Paginate filtered transactions
  const filteredTxns = getFilteredTransactions();
  const totalPages = Math.ceil(filteredTxns.length / rowsPerPage) || 1;
  const paginatedTxns = filteredTxns.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, activeTab]);

  return (
    <div className="flex-1 w-full min-h-screen flex flex-col bg-zinc-950 text-zinc-100 selection:bg-violet-500/30 selection:text-violet-200">
      
      {/* ── Top Header ──────────────────────────────────────────────────────── */}
      <header className="border-b border-zinc-900 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-tr from-violet-600 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Sparkles className="size-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-zinc-50 via-zinc-200 to-zinc-400">
                Alemeno Intel
              </span>
              <span className="text-xs text-zinc-500 ml-2 font-mono">v1.0.0</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1">
              <span className="text-xs text-zinc-400 font-medium whitespace-nowrap">Gemini Key:</span>
              <input
                type="password"
                placeholder="Paste key to enable AI"
                value={geminiKey}
                onChange={(e) => {
                  setGeminiKey(e.target.value);
                  localStorage.setItem("user_gemini_key", e.target.value);
                }}
                className="bg-transparent border-none outline-none text-xs text-zinc-200 placeholder-zinc-600 w-28 focus:w-40 transition-all font-mono"
              />
              {geminiKey ? (
                <div className="size-2 rounded-full bg-emerald-500 animate-pulse" title="API Key Active" />
              ) : (
                <div className="size-2 rounded-full bg-amber-500" title="Key Missing (LLM Fallback Active)" />
              )}
            </div>
            <span className="text-xs text-zinc-400 font-mono hidden md:inline-block px-2 py-1 rounded bg-zinc-900 border border-zinc-800">
              API Base: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
            </span>
          </div>
        </div>
      </header>

      {/* ── View Controller ─────────────────────────────────────────────────── */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col justify-center">
        
        {/* ── View 1: Big Center Upload Screen ─────────────────────────────── */}
        {view === "upload" && (
          <div className="w-full flex-1 flex flex-col items-center justify-center py-10 max-w-3xl mx-auto">
            <div className="text-center mb-8">
              <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white to-zinc-400 mb-3">
                Financial Statement Intelligence
              </h1>
              <p className="text-zinc-400 max-w-lg mx-auto text-sm sm:text-base">
                Drop your credit card or bank ledger CSV here. Our system will isolate anomalies, clean the dataset, and build an AI risk narrative contextually.
              </p>
            </div>

            {/* Big Drag and Drop Box */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={triggerFileInput}
              className={`w-full relative group cursor-pointer transition-all duration-300 p-8 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center text-center gap-5 min-h-[340px] ${
                isDragging
                  ? "border-violet-500 bg-violet-950/20 shadow-[0_0_40px_rgba(139,92,246,0.15)]"
                  : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-900/70"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="hidden"
                disabled={isUploading}
              />
              
              {isUploading ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="size-12 animate-spin text-violet-500" />
                  <p className="text-violet-400 font-semibold">Uploading File...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <div className="p-4 rounded-full bg-zinc-900 border border-zinc-800 group-hover:border-zinc-600 transition-colors flex items-center justify-center">
                    <UploadCloud className="size-10 text-zinc-400 group-hover:text-violet-400 transition-colors" />
                  </div>
                  <div>
                    <p className="text-lg font-medium text-zinc-200">
                      Drag & drop your CSV file here
                    </p>
                    <p className="text-sm text-zinc-500 mt-1">
                      or click to search files (Max size 10MB)
                    </p>
                  </div>
                  <div className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-400">
                    <FileText className="size-3.5 text-zinc-500" />
                    txn_id, date, merchant, amount, currency, status, category, account_id
                  </div>
                </div>
              )}
            </div>

            {/* Recent Uploads Table/Grid */}
            <div className="w-full mt-12">
              <div className="flex items-center justify-between border-b border-zinc-900 pb-3 mb-4">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                  <RefreshCw className="size-3.5" /> Recent Processing Runs
                </h3>
                {recentJobs.length > 0 && (
                  <Button 
                    variant="ghost" 
                    size="xs" 
                    onClick={fetchRecentJobs} 
                    disabled={loadingRecent}
                    className="text-zinc-500 hover:text-zinc-300"
                  >
                    {loadingRecent ? <Loader2 className="size-3 animate-spin" /> : "Refresh"}
                  </Button>
                )}
              </div>

              {loadingRecent && recentJobs.length === 0 ? (
                <div className="py-6 text-center text-zinc-500 text-sm flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin" /> Loading recent files...
                </div>
              ) : recentJobs.length === 0 ? (
                <div className="py-8 text-center text-zinc-500 text-sm rounded-lg border border-zinc-900 bg-zinc-900/10">
                  No records uploaded yet. Upload a statement to get started.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {recentJobs.slice(0, 4).map((job) => (
                    <div
                      key={job.id}
                      onClick={() => {
                        if (job.status === "completed") {
                          startPolling(job.id); // Triggers full fetch and view transition
                        } else if (job.status === "processing" || job.status === "pending") {
                          startPolling(job.id);
                        } else {
                          toast.error(`Job status: ${job.status}. Cannot view results.`);
                        }
                      }}
                      className="group flex flex-col justify-between p-4 rounded-xl border border-zinc-900 bg-zinc-900/30 hover:border-zinc-800 hover:bg-zinc-900/60 transition-all cursor-pointer"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <FileText className="size-4.5 text-zinc-500 shrink-0 group-hover:text-violet-400 transition-colors" />
                          <div className="truncate">
                            <p className="text-sm font-medium text-zinc-300 truncate">
                              {job.filename}
                            </p>
                            <p className="text-[11px] text-zinc-500 font-mono truncate mt-0.5">
                              ID: {job.id.substring(0, 8)}...
                            </p>
                          </div>
                        </div>
                        <Badge
                          variant="outline"
                          className={
                            job.status === "completed"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 capitalize font-medium"
                              : job.status === "failed"
                              ? "bg-rose-500/10 text-rose-400 border-rose-500/20 capitalize font-medium"
                              : "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse capitalize font-medium"
                          }
                        >
                          {job.status}
                        </Badge>
                      </div>

                      <div className="flex items-center justify-between text-xs text-zinc-500 font-mono mt-4 pt-3 border-t border-zinc-900/60">
                        <span>
                          {job.summary?.anomaly_count !== undefined 
                            ? `${job.summary.anomaly_count} Anomaly` 
                            : "—"}
                        </span>
                        <span>
                          {new Date(job.created_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit"
                          })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── View 2: Processing Screen (Glow border wrapper) ──────────────── */}
        {view === "processing" && (
          <div className="w-full max-w-lg mx-auto py-12 flex flex-col items-center">
            {/* The Processing linear gradient glowing border effect */}
            <div className="w-full rounded-2xl p-[1px] bg-gradient-to-r from-violet-600 via-fuchsia-500 to-cyan-400 animate-glow-flow shadow-[0_0_50px_rgba(139,92,246,0.25)]">
              <div className="w-full bg-zinc-950 rounded-[15px] p-8">
                <div className="text-center mb-6">
                  <div className="inline-flex p-3 rounded-full bg-zinc-900/80 border border-zinc-800/80 mb-4 animate-pulse">
                    <Loader2 className="size-6 text-violet-400 animate-spin" />
                  </div>
                  <h2 className="text-xl font-bold text-zinc-100">
                    Analyzing Ledger Statement
                  </h2>
                  <p className="text-xs text-zinc-400 mt-1 font-mono">
                    Job ID: {activeJobId}
                  </p>
                </div>

                {/* Progress bar */}
                <div className="space-y-2 mb-8">
                  <div className="flex justify-between text-xs font-mono text-zinc-500">
                    <span>Task pipeline progress</span>
                    <span>{getPipelineProgress()}%</span>
                  </div>
                  <Progress value={getPipelineProgress()} className="h-2 bg-zinc-900 border border-zinc-800" />
                </div>

                {/* Processing Steps */}
                <div className="space-y-4">
                  {PIPELINE_STEPS.map((step, idx) => {
                    const status = getStepStatus(step.id);
                    return (
                      <div
                        key={step.id}
                        className={`flex items-start gap-4 p-3 rounded-xl border transition-all ${
                          status === "completed"
                            ? "border-emerald-500/10 bg-emerald-500/[0.02]"
                            : status === "active"
                            ? "border-violet-500/30 bg-violet-500/[0.03]"
                            : "border-zinc-900 bg-transparent"
                        }`}
                      >
                        <div className="mt-0.5">
                          {status === "completed" ? (
                            <CheckCircle2 className="size-5 text-emerald-400" />
                          ) : status === "active" ? (
                            <Loader2 className="size-5 text-violet-400 animate-spin" />
                          ) : (
                            <div className="size-5 rounded-full border border-zinc-800 flex items-center justify-center text-xs font-mono text-zinc-600 bg-zinc-950">
                              {idx + 1}
                            </div>
                          )}
                        </div>
                        <div>
                          <p
                            className={`text-sm font-medium ${
                              status === "completed"
                                ? "text-zinc-200"
                                : status === "active"
                                ? "text-violet-300"
                                : "text-zinc-500"
                            }`}
                          >
                            {step.label}
                          </p>
                          <p className="text-xs text-zinc-500 mt-0.5">
                            {step.description}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            
            <p className="text-zinc-500 text-xs mt-6 text-center italic">
              Please don't close this tab. Our asynchronous background workers are compiling results.
            </p>
          </div>
        )}

        {/* ── View 3: Dashboard Results View ────────────────────────────────── */}
        {view === "results" && jobDetails && (
          <div className="w-full flex-1 flex flex-col gap-6 py-6 animate-in fade-in duration-500">
            
            {/* Top Toolbar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-900 pb-5">
              <div className="flex items-start gap-3">
                <Button
                  variant="outline"
                  size="icon-sm"
                  onClick={() => {
                    setView("upload");
                    setJobDetails(null);
                    setActiveJobId(null);
                  }}
                  className="mt-1"
                >
                  <ArrowLeft className="size-4" />
                </Button>
                <div>
                  <div className="flex items-center gap-3">
                    <h1 className="text-2xl font-bold text-white tracking-tight">
                      {jobDetails.filename}
                    </h1>
                    <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 font-medium">
                      Processed
                    </Badge>
                  </div>
                  <p className="text-xs text-zinc-500 mt-1 font-mono">
                    Job Reference ID: {jobDetails.id}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  onClick={() => {
                    setView("upload");
                    setJobDetails(null);
                    setActiveJobId(null);
                  }}
                  className="bg-violet-600 text-white hover:bg-violet-700 hover:shadow-violet-600/20 hover:shadow-lg rounded-lg"
                >
                  Upload New statement
                </Button>
              </div>
            </div>

            {/* KPI Cards Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Card 1: Total volume */}
              <Card className="border-zinc-900 bg-zinc-900/20 backdrop-blur-sm">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <div className="space-y-1">
                    <CardDescription className="text-xs font-mono text-zinc-500 uppercase">
                      Total Cleansed Spend
                    </CardDescription>
                    <CardTitle className="text-2xl font-black text-zinc-100 mt-1">
                      {jobDetails.summary ? formatINR(jobDetails.summary.total_spend_inr) : "₹0"}
                    </CardTitle>
                  </div>
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 text-violet-400">
                    <Wallet className="size-5" />
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-xs text-zinc-400 flex items-center gap-1.5 font-mono">
                    <TrendingUp className="size-3.5 text-emerald-400" />
                    Equivalent: {jobDetails.summary ? formatUSD(jobDetails.summary.total_spend_usd) : "$0.00"}
                  </p>
                </CardContent>
              </Card>

              {/* Card 2: Anomalies detected */}
              <Card className="border-zinc-900 bg-zinc-900/20 backdrop-blur-sm">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <div className="space-y-1">
                    <CardDescription className="text-xs font-mono text-zinc-500 uppercase">
                      Anomalous Activity
                    </CardDescription>
                    <CardTitle className="text-2xl font-black text-rose-400 mt-1">
                      {jobDetails.summary ? jobDetails.summary.anomaly_count : 0}
                    </CardTitle>
                  </div>
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 text-rose-400">
                    <AlertTriangle className="size-5" />
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <span className={`inline-flex px-2 py-0.5 rounded border text-[11px] font-mono font-medium ${getRiskColor(jobDetails.summary?.risk_level)}`}>
                    Overall Risk: {jobDetails.summary?.risk_level || "UNKNOWN"}
                  </span>
                </CardContent>
              </Card>

              {/* Card 3: Cleansing Ratio */}
              <Card className="border-zinc-900 bg-zinc-900/20 backdrop-blur-sm">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <div className="space-y-1">
                    <CardDescription className="text-xs font-mono text-zinc-500 uppercase">
                      Cleansing Yield Ratio
                    </CardDescription>
                    <CardTitle className="text-2xl font-black text-zinc-100 mt-1">
                      {jobDetails.row_count_clean && jobDetails.row_count_raw
                        ? `${Math.round((jobDetails.row_count_clean / jobDetails.row_count_raw) * 100)}%`
                        : "100%"}
                    </CardTitle>
                  </div>
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 text-cyan-400">
                    <Layers className="size-5" />
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-xs text-zinc-400 font-mono">
                    Kept {jobDetails.row_count_clean} / {jobDetails.row_count_raw} records
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Dashboard Workspace */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* LEFT / MAIN COLUMN: AI brief + detailed table */}
              <div className="lg:col-span-2 space-y-6">
                
                {/* AI Risk Brief */}
                <Card className="border-zinc-900 bg-zinc-900/10 overflow-hidden relative">
                  <div className="absolute top-0 right-0 p-4 opacity-5">
                    <Sparkles className="size-24 text-violet-400" />
                  </div>
                  <CardHeader className="border-b border-zinc-900 bg-zinc-900/30 flex flex-row items-center justify-between py-4">
                    <div>
                      <CardTitle className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                        <Sparkles className="size-4 text-violet-400 fill-violet-400/20" /> AI-Generated Risk Intelligence Brief
                      </CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="p-6">
                    {jobDetails.summary?.llm_failed ? (
                      <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-4 flex gap-3 text-sm text-yellow-300">
                        <Info className="size-5 shrink-0 mt-0.5 text-yellow-400" />
                        <div>
                          <p className="font-semibold text-yellow-200">LLM Generation Fallback (Rate Limited)</p>
                          <p className="text-xs text-yellow-400/80 mt-1">
                            The AI assistant encountered a Gemini service rate limit. Showing local rule fallback narrative:
                          </p>
                          <p className="mt-3 italic text-zinc-300">
                            {jobDetails.summary?.narrative || "No narrative fallback generated."}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm leading-relaxed text-zinc-300 whitespace-pre-line font-sans">
                        {jobDetails.summary?.narrative || "No narrative analysis available for this statement."}
                      </p>
                    )}
                  </CardContent>
                </Card>

                {/* Detailed Table Card */}
                <Card className="border-zinc-900 bg-zinc-900/10">
                  <CardHeader className="pb-4 border-b border-zinc-900 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <CardTitle className="text-sm font-bold text-zinc-100">Transaction Registry</CardTitle>
                      <CardDescription className="text-xs text-zinc-500 mt-1">
                        View and filter clean records or anomalous transactions
                      </CardDescription>
                    </div>
                    
                    {/* Tab Toggles */}
                    <div className="flex border border-zinc-900 bg-zinc-950 p-1 rounded-lg shrink-0 w-fit self-start">
                      <button
                        onClick={() => setActiveTab("all")}
                        className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
                          activeTab === "all"
                            ? "bg-zinc-800 text-zinc-100 shadow"
                            : "text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        All ({jobDetails.transactions?.length || 0})
                      </button>
                      <button
                        onClick={() => setActiveTab("anomalies")}
                        className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
                          activeTab === "anomalies"
                            ? "bg-rose-500/10 text-rose-400 shadow"
                            : "text-zinc-500 hover:text-zinc-300"
                        }`}
                      >
                        Anomalies ({jobDetails.summary?.anomaly_count || 0})
                      </button>
                    </div>
                  </CardHeader>

                  <CardContent className="p-0">
                    
                    {/* Search inputs */}
                    <div className="p-4 border-b border-zinc-900 flex items-center gap-3">
                      <div className="relative flex-1">
                        <Search className="absolute left-3 top-2.5 size-4 text-zinc-500" />
                        <input
                          type="text"
                          placeholder="Search merchant, category, txn_id..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          className="w-full bg-zinc-950 border border-zinc-900 hover:border-zinc-800 focus:border-violet-500 rounded-lg pl-9 pr-4 py-2 text-xs text-zinc-200 outline-none placeholder-zinc-600 transition-all"
                        />
                      </div>
                    </div>

                    {/* Table element */}
                    {paginatedTxns.length === 0 ? (
                      <div className="py-12 text-center text-zinc-600 text-xs">
                        No transactions match the selected criteria.
                      </div>
                    ) : (
                      <Table>
                        <TableHeader className="border-b border-zinc-900">
                          <TableRow className="hover:bg-transparent border-zinc-900">
                            <TableHead className="font-mono text-xs w-[110px] pl-4">Date</TableHead>
                            <TableHead className="text-xs">Merchant</TableHead>
                            <TableHead className="text-xs hidden sm:table-cell">Category</TableHead>
                            <TableHead className="text-xs text-right">Amount</TableHead>
                            <TableHead className="text-xs w-[120px] text-center pr-4">Anomaly</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-zinc-900">
                          {paginatedTxns.map((txn, index) => (
                            <React.Fragment key={txn.txn_id || index}>
                              <TableRow className={`border-zinc-900/60 ${txn.is_anomaly ? "bg-rose-950/5 hover:bg-rose-950/10" : ""}`}>
                                <TableCell className="font-mono text-zinc-500 text-xs pl-4">{txn.date}</TableCell>
                                <TableCell className="font-medium text-zinc-200 text-xs">
                                  <div className="truncate max-w-[150px] sm:max-w-[200px]" title={txn.merchant}>
                                    {txn.merchant}
                                  </div>
                                </TableCell>
                                <TableCell className="hidden sm:table-cell text-xs">
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-zinc-900 text-zinc-400 border border-zinc-800/60">
                                    {txn.category}
                                  </span>
                                </TableCell>
                                <TableCell className={`text-right font-semibold text-xs font-mono ${txn.is_anomaly ? "text-rose-400" : "text-zinc-300"}`}>
                                  {txn.currency === "INR" || txn.currency === "Rs" 
                                    ? formatINR(txn.amount)
                                    : formatUSD(txn.amount)}
                                </TableCell>
                                <TableCell className="text-center pr-4">
                                  {txn.is_anomaly ? (
                                    <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                                      Flagged
                                    </span>
                                  ) : (
                                    <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-mono bg-zinc-950 text-zinc-500 border border-zinc-900/60">
                                      Normal
                                    </span>
                                  )}
                                </TableCell>
                              </TableRow>
                              {txn.is_anomaly && txn.anomaly_reason && (
                                <tr className="bg-rose-950/5 hover:bg-rose-950/10 border-b border-zinc-900/60">
                                  <td colSpan={5} className="py-2 px-4 text-[11px] text-rose-400/90 italic pl-14">
                                    Reason: {txn.anomaly_reason}
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          ))}
                        </TableBody>
                      </Table>
                    )}

                    {/* Pagination Footer */}
                    {totalPages > 1 && (
                      <div className="p-4 border-t border-zinc-900 flex items-center justify-between text-xs font-mono text-zinc-500">
                        <span>
                          Page {currentPage} of {totalPages} ({filteredTxns.length} items)
                        </span>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="xs"
                            disabled={currentPage === 1}
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                          >
                            Prev
                          </Button>
                          <Button
                            variant="outline"
                            size="xs"
                            disabled={currentPage === totalPages}
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                          >
                            Next
                          </Button>
                        </div>
                      </div>
                    )}

                  </CardContent>
                </Card>
              </div>

              {/* RIGHT COLUMN: Spend Category Breakdown + Top Merchants */}
              <div className="space-y-6">
                
                {/* Category breakdown card */}
                <Card className="border-zinc-900 bg-zinc-900/10">
                  <CardHeader className="border-b border-zinc-900 py-4">
                    <CardTitle className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                      Category Spend Volume
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-5 space-y-4">
                    {(() => {
                      const breakdown = jobDetails.summary?.category_breakdown || {};
                      const categories = Object.keys(breakdown);
                      
                      if (categories.length === 0) {
                        return <div className="text-center text-xs text-zinc-500">No category breakdown data.</div>;
                      }

                      // Find max value for percentages
                      const maxVal = Math.max(...Object.values(breakdown), 1);
                      const totalSum = Object.values(breakdown).reduce((a, b) => a + b, 0);

                      return (
                        <div className="space-y-3.5">
                          {categories
                            .map(cat => ({ name: cat, amount: breakdown[cat] }))
                            .sort((a, b) => b.amount - a.amount)
                            .map((item, idx) => {
                              const pctOfMax = (item.amount / maxVal) * 100;
                              const pctOfTotal = (item.amount / totalSum) * 100;
                              
                              return (
                                <div key={idx} className="space-y-1.5">
                                  <div className="flex justify-between text-xs">
                                    <span className="text-zinc-300 font-medium truncate max-w-[160px]">
                                      {item.name}
                                    </span>
                                    <span className="font-mono text-zinc-400 font-semibold">
                                      {formatINR(item.amount)}
                                    </span>
                                  </div>
                                  <div className="h-2 w-full rounded-full bg-zinc-950 overflow-hidden border border-zinc-900/60 relative">
                                    <div
                                      style={{ width: `${pctOfMax}%` }}
                                      className="h-full rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 transition-all duration-500"
                                    />
                                  </div>
                                  <div className="flex justify-between text-[10px] font-mono text-zinc-600">
                                    <span>Ratio</span>
                                    <span>{pctOfTotal.toFixed(1)}% of total</span>
                                  </div>
                                </div>
                              );
                            })}
                        </div>
                      );
                    })()}
                  </CardContent>
                </Card>

                {/* Top Merchants Card */}
                <Card className="border-zinc-900 bg-zinc-900/10">
                  <CardHeader className="border-b border-zinc-900 py-4">
                    <CardTitle className="text-sm font-bold text-zinc-100">Top Merchants by Spend</CardTitle>
                  </CardHeader>
                  <CardContent className="p-5">
                    {(() => {
                      const merchants = jobDetails.summary?.top_merchants || [];
                      
                      if (merchants.length === 0) {
                        return <div className="text-center text-xs text-zinc-500">No merchant spend data.</div>;
                      }

                      const maxSpend = merchants[0]?.total || 1;

                      return (
                        <div className="space-y-3.5">
                          {merchants.map((m, idx) => {
                            const pctOfMax = (m.total / maxSpend) * 100;
                            return (
                              <div key={idx} className="space-y-1.5">
                                <div className="flex justify-between text-xs">
                                  <span className="text-zinc-300 font-medium truncate max-w-[160px]">
                                    {m.merchant}
                                  </span>
                                  <span className="font-mono text-zinc-400 font-semibold">
                                    {formatINR(m.total)}
                                  </span>
                                </div>
                                <div className="h-1.5 w-full rounded-full bg-zinc-950 overflow-hidden border border-zinc-900/60 relative">
                                  <div
                                    style={{ width: `${pctOfMax}%` }}
                                    className="h-full rounded-full bg-cyan-500/70 transition-all duration-500"
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      );
                    })()}
                  </CardContent>
                </Card>

              </div>

            </div>

          </div>
        )}

      </div>
    </div>
  );
}
