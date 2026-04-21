export const DEFAULT_PAGE_SIZE = 25;
export const DEFAULT_PAGE_INFO: PageInfo = {total: 0, index: 0, size: DEFAULT_PAGE_SIZE};

export interface PageInfo {
  total: number;
  index: number;
  size: number;
}

export interface PageResponse<T> {
  items: T[];
  page_info: PageInfo;
}

export function toPageResponse<T>(all_items: T[], page_index: number, size: number): PageResponse<T> {
  const offset = page_index * size;
  const page_items = all_items.slice(offset + 1, offset + 1 + size);

  return {items: page_items, page_info: {total: all_items.length, index: page_index, size}};
}
