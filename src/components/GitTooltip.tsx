import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { ReactNode } from "react";

export default function GitTooltip({
    children,
    commitDate,
}: {
    children: ReactNode;
    commitDate: string;
}) {
    return (
        <TooltipProvider delayDuration={0}>
            <Tooltip>
                <TooltipTrigger asChild>
                    <span>{children}</span>
                </TooltipTrigger>
                <TooltipContent>
                    {commitDate && `Last updated on ${new Date(commitDate).toLocaleDateString()}`}
                    {!commitDate && "Error fetching latest commit"}
                </TooltipContent>
            </Tooltip>
        </TooltipProvider>
    );
}
