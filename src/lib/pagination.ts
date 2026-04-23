export function getPageNumbers(current: number, total: number): (number | "...")[] {
    if (total <= 3) return Array.from({ length: total }, (_, i) => i + 1);

    const pages: (number | "...")[] = [];

    if (current === 1) {
        pages.push(1, 2, 3);
        if (total > 4) pages.push("...");
        if (total > 3) pages.push(total);
    } else if (current === total) {
        if (total > 3) pages.push(1);
        if (total > 4) pages.push("...");
        pages.push(total - 2, total - 1, total);
    } else {
        if (current > 2) {
            pages.push(1);
            if (current > 3) pages.push("...");
        }
        pages.push(current - 1, current, current + 1);
        if (current < total - 1) {
            if (current < total - 2) pages.push("...");
            pages.push(total);
        }
    }

    return pages;
}
