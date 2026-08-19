/**
 * Tensioned Signal Web: route surfaces separate the user-driven product, evidence inspection, Judge Mode replay, and benchmark context.
 */
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Benchmark from "./pages/Benchmark";
import CaseDetail from "./pages/CaseDetail";
import Cases from "./pages/Cases";
import DownstreamOutput from "./pages/DownstreamOutput";
import Evidence from "./pages/Evidence";
import Home from "./pages/Home";
import JudgeMode from "./pages/JudgeMode";
import NotFound from "./pages/NotFound";
import SilentCorruption from "./pages/SilentCorruption";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/cases" component={Cases} />
      <Route path="/cases/:caseId" component={CaseDetail} />
      <Route path="/evidence" component={Evidence} />
      <Route path="/judge" component={JudgeMode} />
      <Route path="/silent-corruption" component={SilentCorruption} />
      <Route path="/benchmark" component={Benchmark} />
      <Route path="/downstream" component={DownstreamOutput} />
      <Route component={NotFound} />
    </Switch>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark">
        <TooltipProvider><Toaster theme="dark" position="bottom-right" /><Router /></TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
