import { useEffect, useState } from "react";
import { GitCommitHorizontal } from "lucide-react";
import GitTooltip from "./GitTooltip";

type CommitData = {
    shortSha: string;
    commitUrl: string;
    commitDate: string;
};

export default function GithubCommit() {
    const [data, setData] = useState<CommitData | null>(null);

    useEffect(() => {
        const controller = new AbortController();
        (async () => {
            try {
                const r = await fetch("/api/git-commit", { signal: controller.signal });
                if (!r.ok) return;
                const d = await r.json();
                if (!d.error) setData(d);
            } catch {}
        })();
        return () => controller.abort();
    }, []);

    return (
        <GitTooltip commitDate={data?.commitDate ?? ""}>
            <a
                href={data?.commitUrl ?? "#"}
                target="_blank"
                rel="noreferrer noopener"
                className="flex items-center gap-2 hover:text-accent duration-200 group"
            >
                <GitCommitHorizontal
                    className="mt-0.5 w-4 h-4 text-muted group-hover:text-accent duration-200"
                    aria-hidden="true"
                />
                <span>{data?.shortSha ?? "loading..."}</span>
            </a>
        </GitTooltip>
    );
}
