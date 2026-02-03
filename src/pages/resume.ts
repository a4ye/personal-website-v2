export const prerender = false;

export async function GET() {
    const resumeUrl = "https://old.aaronye.dev/resume.pdf";

    const response = await fetch(resumeUrl);

    if (!response.ok) {
        return new Response("Failed to fetch resume", {
            status: response.status,
        });
    }

    const pdfBuffer = await response.arrayBuffer();

    return new Response(pdfBuffer, {
        headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": "inline; filename=\"resume.pdf\"",
        },
    });
}
