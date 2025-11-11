export interface CreateBookRequest {
  id: string;
  title: string;
  pdf_temp_file_id: string;
}

export interface BookDetails {
  id: string;
  title: string;
  pdf_file_name: string;
}
