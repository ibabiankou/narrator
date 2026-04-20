export const EMPTY_PAGE_RESPONSE = {items: [], total: 0, page: 0, size: 0};
export interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export function toPageResponse<T>(all_items: T[], page: number, size: number): PageResponse<T> {
  const offset = (page - 1) * size;
  const page_items = all_items.slice(offset + 1, offset + 1 + size);

  return {items: page_items, total: all_items.length, page, size};
}
