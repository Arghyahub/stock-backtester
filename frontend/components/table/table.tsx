"use client";

import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table";
import { ChevronDown, ChevronUp, ChevronsUpDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Filter, FilterX } from "lucide-react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";

// ─── Types ──────────────────────────────────────────────────────────────────────

type FilterType = "text" | "number" | "select" | "date";

export type DataTableColumnConfig<T = any> = {
  key: Extract<keyof T, string> | string;
  title: string;
  filter_type?: FilterType;
  onClick?: (row: T) => any;
  component?: (row: T) => React.ReactNode;
};

type Props<T> = {
  columns: DataTableColumnConfig<T>[];
  data: T[];
  manualSorting?: boolean;
  manualFiltering?: boolean;
  manualPagination?: boolean;
  pageCount?: number;
  rowCount?: number;
  HeaderComponent?: React.ReactNode;
};

// ─── Helpers ────────────────────────────────────────────────────────────────────

/** Build a new URLSearchParams from the current one and a set of updates.
 *  Pass `null` / `undefined` / `""` to remove a key. */
function patchParams(
  current: URLSearchParams,
  updates: Record<string, string | null | undefined>
): URLSearchParams {
  const next = new URLSearchParams(current.toString());
  for (const [k, v] of Object.entries(updates)) {
    if (v == null || v === "") {
      next.delete(k);
    } else {
      next.set(k, v);
    }
  }
  return next;
}

// ─── Filter inputs ──────────────────────────────────────────────────────────────

const inputBase =
  "w-full rounded-md border border-outline-variant bg-surface-container-lowest px-2.5 py-1.5 text-xs text-on-surface placeholder:text-on-surface-variant/50 outline-none transition-all focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20";

function TextFilter({
  columnKey,
  value,
  onChange,
}: {
  columnKey: string;
  value: string;
  onChange: (key: string, value: string) => void;
}) {
  const timeout = useRef<ReturnType<typeof setTimeout>>(null);
  const [local, setLocal] = useState(value);

  useEffect(() => setLocal(value), [value]);

  return (
    <input
      type="text"
      placeholder="Filter…"
      className={inputBase}
      value={local}
      onChange={(e) => {
        setLocal(e.target.value);
        if (timeout.current) clearTimeout(timeout.current);
        timeout.current = setTimeout(() => onChange(columnKey, e.target.value), 300);
      }}
    />
  );
}

function NumberFilter({
  columnKey,
  minValue,
  maxValue,
  onChange,
}: {
  columnKey: string;
  minValue: string;
  maxValue: string;
  onChange: (key: string, value: string, type: "min" | "max") => void;
}) {
  return (
    <div className="flex flex-col gap-1 w-full">
      <div className="flex items-center gap-1 w-full">
        <span className="text-xs text-on-surface-variant w-5 shrink-0 text-right">&gt;=</span>
        <input
          type="number"
          placeholder="Min"
          className={`${inputBase} flex-1`}
          value={minValue}
          onChange={(e) => onChange(columnKey, e.target.value, "min")}
        />
      </div>
      <div className="flex items-center gap-1 w-full">
        <span className="text-xs text-on-surface-variant w-5 shrink-0 text-right">&lt;=</span>
        <input
          type="number"
          placeholder="Max"
          className={`${inputBase} flex-1`}
          value={maxValue}
          onChange={(e) => onChange(columnKey, e.target.value, "max")}
        />
      </div>
    </div>
  );
}

function DateFilter({
  columnKey,
  fromValue,
  toValue,
  onChange,
}: {
  columnKey: string;
  fromValue: string;
  toValue: string;
  onChange: (key: string, value: string, type: "from" | "to") => void;
}) {
  const toLocalString = (val: string) => {
    if (!val) return "";
    const d = new Date(val);
    if (isNaN(d.getTime())) return val;
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  const handleDateChange = (val: string, type: "from" | "to") => {
    if (!val) {
      onChange(columnKey, "", type);
      return;
    }
    const d = new Date(val);
    if (!isNaN(d.getTime())) {
      onChange(columnKey, d.toISOString(), type);
    } else {
      onChange(columnKey, val, type);
    }
  };

  return (
    <div className="flex flex-col gap-1 w-full">
      <div className="flex items-center gap-1 w-full">
        <span className="text-xs text-on-surface-variant w-5 shrink-0 text-right">&gt;=</span>
        <input
          type="datetime-local"
          className={`${inputBase} flex-1`}
          value={toLocalString(fromValue)}
          onChange={(e) => handleDateChange(e.target.value, "from")}
        />
      </div>
      <div className="flex items-center gap-1 w-full">
        <span className="text-xs text-on-surface-variant w-5 shrink-0 text-right">&lt;=</span>
        <input
          type="datetime-local"
          className={`${inputBase} flex-1`}
          value={toLocalString(toValue)}
          onChange={(e) => handleDateChange(e.target.value, "to")}
        />
      </div>
    </div>
  );
}

function SelectFilter({
  columnKey,
  value,
  options,
  onChange,
}: {
  columnKey: string;
  value: string;
  options: string[];
  onChange: (key: string, value: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = useMemo(
    () => options.filter((opt) => opt.toLowerCase().includes(search.toLowerCase())),
    [options, search]
  );

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        placeholder={value || "All"}
        className={`${inputBase} cursor-pointer ${value ? "font-medium text-on-surface" : ""}`}
        value={open ? search : value}
        onFocus={() => {
          setOpen(true);
          setSearch("");
        }}
        onChange={(e) => setSearch(e.target.value)}
      />
      {/* Dropdown chevron */}
      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-on-surface-variant/50" />

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-outline-variant bg-surface-container-lowest shadow-lg">
          {/* "All" option to clear */}
          <button
            type="button"
            className={`w-full px-2.5 py-1.5 text-left text-xs transition-colors hover:bg-brand-primary/10 ${
              !value ? "font-semibold text-brand-primary" : "text-on-surface-variant"
            }`}
            onMouseDown={(e) => {
              e.preventDefault();
              onChange(columnKey, "");
              setOpen(false);
              setSearch("");
            }}
          >
            All
          </button>

          {filtered.length === 0 ? (
            <div className="px-2.5 py-3 text-center text-xs text-on-surface-variant/60">
              No matches
            </div>
          ) : (
            filtered.map((opt) => (
              <button
                key={opt}
                type="button"
                className={`w-full px-2.5 py-1.5 text-left text-xs transition-colors hover:bg-brand-primary/10 ${
                  value === opt ? "bg-brand-primary/5 font-semibold text-brand-primary" : "text-on-surface"
                }`}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onChange(columnKey, opt);
                  setOpen(false);
                  setSearch("");
                }}
              >
                {opt}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ─── Pagination button ─────────────────────────────────────────────────────────

function PagButton({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void;
  disabled: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center justify-center rounded-md border border-outline-variant bg-surface-container-lowest p-1.5 text-on-surface transition-colors hover:bg-surface-container-low disabled:pointer-events-none disabled:opacity-40"
    >
      {children}
    </button>
  );
}

// ─── Main Table Component ───────────────────────────────────────────────────────

function DataTable<T>({ columns: columnConfigs, data, manualSorting, manualFiltering, manualPagination, pageCount, rowCount, HeaderComponent }: Props<T>) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // ── Read URL state ──────────────────────────────────────────────────────────

  const initialSorting = useMemo<SortingState>(() => {
    const sort = searchParams.get("sort");
    const order = searchParams.get("order");
    if (sort && (order === "asc" || order === "desc")) {
      return [{ id: sort, desc: order === "desc" }];
    }
    return [];
  }, [searchParams]);

  const initialPage = useMemo(() => {
    const p = searchParams.get("page");
    return p ? Math.max(0, parseInt(p, 10) - 1) : 0;
  }, [searchParams]);

  const initialColumnFilters = useMemo<ColumnFiltersState>(() => {
    const filters: ColumnFiltersState = [];
    for (const col of columnConfigs) {
      const val = searchParams.get(col.key as string);
      if (!val) continue;

      if (col.filter_type === "number" || col.filter_type === "date") {
        try {
          const parsed = JSON.parse(val);
          if (Array.isArray(parsed) && parsed.length === 2) {
            filters.push({ id: col.key as string, value: parsed });
          }
        } catch {
          // invalid json, ignore
        }
      } else {
        filters.push({ id: col.key as string, value: val });
      }
    }
    return filters;
  }, [searchParams, columnConfigs]);

  // ── State ───────────────────────────────────────────────────────────────────

  const [sorting, setSorting] = useState<SortingState>(initialSorting);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>(initialColumnFilters);
  const [showFilters, setShowFilters] = useState(initialColumnFilters.length > 0);
  const [pageIndex, setPageIndex] = useState(initialPage);
  const pageSize = 20;

  // ── Sync state → URL ────────────────────────────────────────────────────────

  const pushParams = useCallback(
    (updates: Record<string, string | null | undefined>) => {
      const next = patchParams(searchParams, updates);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [router, pathname, searchParams]
  );

  // Sorting → URL
  useEffect(() => {
    if (sorting.length === 0) {
      pushParams({ sort: null, order: null });
    } else {
      pushParams({ sort: sorting[0].id, order: sorting[0].desc ? "desc" : "asc" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sorting]);

  // Page → URL
  useEffect(() => {
    pushParams({ page: pageIndex > 0 ? String(pageIndex + 1) : null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageIndex]);

  // Column filters → URL
  useEffect(() => {
    const updates: Record<string, string | null> = {};

    // Clear all filter params first
    for (const col of columnConfigs) {
      updates[col.key as string] = null;
    }

    // Set active filter params
    for (const f of columnFilters) {
      const col = columnConfigs.find((c) => c.key === f.id);
      if (!col) continue;

      if ((col.filter_type === "number" || col.filter_type === "date") && Array.isArray(f.value)) {
        if (f.value[0] || f.value[1]) {
          updates[col.key as string] = JSON.stringify(f.value);
        }
      } else if (typeof f.value === "string" && f.value) {
        updates[col.key as string] = f.value as string;
      }
    }

    pushParams(updates);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [columnFilters]);

  // ── Build column definitions ────────────────────────────────────────────────

  const tanstackColumns = useMemo<ColumnDef<T>[]>(() => {
    return columnConfigs.map((col) => {
      const def: ColumnDef<T> = {
        id: col.key as string,
        accessorKey: col.key as string,
        header: col.title,
        enableSorting: true,
      };

      // Custom filter function per type
      if (col.filter_type === "number") {
        def.filterFn = (row, columnId, filterValue) => {
          const val = Number(row.getValue(columnId));
          const [min, max] = filterValue as [string, string];
          if (min && val < Number(min)) return false;
          if (max && val > Number(max)) return false;
          return true;
        };
      } else if (col.filter_type === "date") {
        def.filterFn = (row, columnId, filterValue) => {
          const raw = row.getValue(columnId);
          if (!raw) return false;
          const val = new Date(raw as string).getTime();
          const [from, to] = filterValue as [string, string];
          if (from && val < new Date(from).getTime()) return false;
          if (to && val > new Date(to).getTime()) return false;
          return true;
        };
        // Sort dates properly
        def.sortingFn = (a, b, columnId) => {
          const da = new Date(a.getValue(columnId) as string).getTime();
          const db = new Date(b.getValue(columnId) as string).getTime();
          return da - db;
        };
      } else if (col.filter_type === "select") {
        def.filterFn = (row, columnId, filterValue) => {
          if (!filterValue) return true;
          return String(row.getValue(columnId)) === filterValue;
        };
      } else {
        // text — case-insensitive includes
        def.filterFn = (row, columnId, filterValue) => {
          if (!filterValue) return true;
          return String(row.getValue(columnId))
            .toLowerCase()
            .includes(String(filterValue).toLowerCase());
        };
      }

      // Format dates nicely in cells or use custom component
      if (col.component) {
        def.cell = ({ row }) => col.component!(row.original);
      } else if (col.filter_type === "date") {
        def.cell = ({ getValue }) => {
          const raw = getValue();
          if (!raw) return "—";
          const d = new Date(raw as string);
          return isNaN(d.getTime()) ? String(raw) : d.toLocaleString("en-IN", { 
            day: "2-digit", month: "short", year: "numeric",
            hour: "2-digit", minute: "2-digit"
          });
        };
      }

      return def;
    });
  }, [columnConfigs]);

  // ── Unique values for select filters ────────────────────────────────────────

  const selectOptions = useMemo(() => {
    const map: Record<string, string[]> = {};
    for (const col of columnConfigs) {
      if (col.filter_type === "select") {
        const unique = Array.from(new Set(data.map((r) => String((r as any)[col.key] ?? "")))).filter(Boolean).sort();
        map[col.key as string] = unique;
      }
    }
    return map;
  }, [columnConfigs, data]);

  // ── Table instance ──────────────────────────────────────────────────────────

  const table = useReactTable({
    data,
    columns: tanstackColumns,
    state: { sorting, columnFilters, pagination: { pageIndex, pageSize } },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: (updater) => {
      const next = typeof updater === "function" ? updater({ pageIndex, pageSize }) : updater;
      setPageIndex(next.pageIndex);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    enableSortingRemoval: true,
    manualSorting,
    manualFiltering,
    manualPagination,
    pageCount,
    rowCount,
  });

  // ── Filter change handlers ──────────────────────────────────────────────────

  const handleTextFilterChange = useCallback(
    (key: string, value: string) => {
      table.getColumn(key)?.setFilterValue(value || undefined);
    },
    [table]
  );

  const handleNumberFilterChange = useCallback(
    (key: string, value: string, type: "min" | "max") => {
      const col = table.getColumn(key);
      if (!col) return;
      const current = (col.getFilterValue() as [string, string]) ?? ["", ""];
      const next: [string, string] = type === "min" ? [value, current[1]] : [current[0], value];
      col.setFilterValue(next[0] || next[1] ? next : undefined);
    },
    [table]
  );

  const handleDateFilterChange = useCallback(
    (key: string, value: string, type: "from" | "to") => {
      const col = table.getColumn(key);
      if (!col) return;
      const current = (col.getFilterValue() as [string, string]) ?? ["", ""];
      const next: [string, string] = type === "from" ? [value, current[1]] : [current[0], value];
      col.setFilterValue(next[0] || next[1] ? next : undefined);
    },
    [table]
  );

  const handleSelectFilterChange = useCallback(
    (key: string, value: string) => {
      table.getColumn(key)?.setFilterValue(value || undefined);
    },
    [table]
  );

  // ── Render ──────────────────────────────────────────────────────────────────

  const totalRows = rowCount ?? table.getFilteredRowModel().rows.length;

  return (
    <div className="flex flex-col gap-3">
      {/* Table Actions */}
      <div className="flex flex-row">
        {HeaderComponent}
        <button
          onClick={() => {
            if (showFilters) {
              setColumnFilters([]);
            }
            setShowFilters(!showFilters);
          }}
          className={`inline-flex ml-auto items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
            showFilters 
              ? "border-brand-primary bg-brand-primary/10 text-brand-primary hover:bg-brand-primary/20" 
              : "border-outline-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container-low"
          }`}
        >
          {showFilters ? <FilterX className="h-4 w-4" /> : <Filter className="h-4 w-4" />}
          {showFilters ? "Clear Filters" : "Filter"}
        </button>
      </div>

      {/* Table container */}
      <div className="overflow-auto rounded-xl border border-outline-variant bg-surface-container-lowest shadow-sm">
        <table className="w-full border-collapse text-sm">
          {/* ─ Header ──────────────────────────────────────────────────── */}
          <thead className="sticky top-0 z-10">
            {table.getHeaderGroups().map((headerGroup) => (
              <React.Fragment key={headerGroup.id}>
                {/* Column titles + sort controls */}
                <tr className="bg-surface-container-low">
                  {headerGroup.headers.map((header) => {
                    const isSorted = header.column.getIsSorted();
                    return (
                      <th
                        key={header.id}
                        className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-on-surface-variant select-none"
                      >
                        <button
                          type="button"
                          className="inline-flex items-center gap-1.5 transition-colors hover:text-on-surface"
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          <span className="flex flex-col -space-y-1">
                            <ChevronUp
                              className={`h-3.5 w-3.5 transition-colors ${isSorted === "asc" ? "text-brand-primary" : "text-on-surface-variant/30"}`}
                            />
                            <ChevronDown
                              className={`h-3.5 w-3.5 transition-colors ${isSorted === "desc" ? "text-brand-primary" : "text-on-surface-variant/30"}`}
                            />
                          </span>
                        </button>
                      </th>
                    );
                  })}
                </tr>

                {/* Filter row */}
                {showFilters && (
                  <tr className="border-b border-outline-variant bg-surface-container-low/60">
                    {headerGroup.headers.map((header) => {
                      const col = columnConfigs.find((c) => c.key === header.column.id);
                      const filterValue = header.column.getFilterValue();

                      return (
                        <th key={`filter-${header.id}`} className="px-4 py-2">
                          {col?.filter_type === "text" && (
                            <TextFilter
                              columnKey={col.key as string}
                              value={(filterValue as string) ?? ""}
                              onChange={handleTextFilterChange}
                            />
                          )}
                          {col?.filter_type === "number" && (
                            <NumberFilter
                              columnKey={col.key as string}
                              minValue={((filterValue as [string, string]) ?? ["", ""])[0]}
                              maxValue={((filterValue as [string, string]) ?? ["", ""])[1]}
                              onChange={handleNumberFilterChange}
                            />
                          )}
                          {col?.filter_type === "date" && (
                            <DateFilter
                              columnKey={col.key as string}
                              fromValue={((filterValue as [string, string]) ?? ["", ""])[0]}
                              toValue={((filterValue as [string, string]) ?? ["", ""])[1]}
                              onChange={handleDateFilterChange}
                            />
                          )}
                          {col?.filter_type === "select" && (
                            <SelectFilter
                              columnKey={col.key as string}
                              value={(filterValue as string) ?? ""}
                              options={selectOptions[col.key as string] ?? []}
                              onChange={handleSelectFilterChange}
                            />
                          )}
                        </th>
                      );
                    })}
                  </tr>
                )}
              </React.Fragment>
            ))}
          </thead>

          {/* ─ Body ────────────────────────────────────────────────────── */}
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columnConfigs.length}
                  className="py-12 text-center text-sm text-on-surface-variant"
                >
                  No results found.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row, i) => (
                <tr
                  key={row.id}
                  className={`border-b border-outline-variant/50 transition-colors hover:bg-brand-primary/5 ${
                    i % 2 === 0 ? "bg-surface-container-lowest" : "bg-surface-primary/40"
                  }`}
                >
                  {row.getVisibleCells().map((cell) => {
                    const colConfig = columnConfigs.find((c) => c.key === cell.column.id);
                    return (
                      <td
                        key={cell.id}
                        className={`whitespace-nowrap px-4 py-2.5 text-sm text-on-surface ${colConfig?.onClick ? "cursor-pointer hover:underline text-brand-primary" : ""}`}
                        onClick={colConfig?.onClick ? () => colConfig.onClick!(row.original) : undefined}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ─ Pagination ────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-outline-variant bg-surface-container-low px-4 py-2.5 text-xs text-on-surface-variant">
        <span>
          Showing{" "}
          <span className="font-medium text-on-surface">
            {totalRows === 0 ? 0 : pageIndex * pageSize + 1}
          </span>
          –
          <span className="font-medium text-on-surface">
            {Math.min((pageIndex + 1) * pageSize, totalRows)}
          </span>{" "}
          of <span className="font-medium text-on-surface">{totalRows}</span> rows
        </span>

        <div className="flex items-center gap-1.5">
          <PagButton onClick={() => { setPageIndex(0); }} disabled={!table.getCanPreviousPage()}>
            <ChevronsLeft className="h-4 w-4" />
          </PagButton>
          <PagButton onClick={() => { setPageIndex((p) => p - 1); }} disabled={!table.getCanPreviousPage()}>
            <ChevronLeft className="h-4 w-4" />
          </PagButton>

          <span className="mx-2 tabular-nums">
            Page <span className="font-medium text-on-surface">{pageIndex + 1}</span> of{" "}
            <span className="font-medium text-on-surface">{table.getPageCount() || 1}</span>
          </span>

          <PagButton onClick={() => { setPageIndex((p) => p + 1); }} disabled={!table.getCanNextPage()}>
            <ChevronRight className="h-4 w-4" />
          </PagButton>
          <PagButton onClick={() => { setPageIndex(table.getPageCount() - 1); }} disabled={!table.getCanNextPage()}>
            <ChevronsRight className="h-4 w-4" />
          </PagButton>
        </div>
      </div>
    </div>
  );
}

export default memo(DataTable) as <T>(props: Props<T> & { key?: React.Key }) => ReturnType<typeof DataTable>;