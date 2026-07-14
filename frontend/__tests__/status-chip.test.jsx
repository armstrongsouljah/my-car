import { render, screen } from "@testing-library/react";
import StatusChip from "@/components/StatusChip";

describe("StatusChip", () => {
  it("renders the overdue state", () => {
    render(<StatusChip status="overdue" />);
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });

  it("renders the due soon state", () => {
    render(<StatusChip status="due_soon" />);
    expect(screen.getByText("Due soon")).toBeInTheDocument();
  });

  it("falls back to ok styling for unknown statuses", () => {
    render(<StatusChip status="something_new" />);
    expect(screen.getByText("something_new")).toBeInTheDocument();
  });
});
