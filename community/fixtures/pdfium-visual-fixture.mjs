// Deterministic local PDFium facade: production never imports this fixture.
export function pdfiumVisualFixture(){
  const heap=new Uint8Array(1024*1024);let width,height;
  return {pdfium:{HEAPU8:heap,wasmExports:{malloc:()=>1,free(){}}},FPDF_LoadMemDocument:()=>1,FPDF_GetPageCount:()=>2,
    FPDF_LoadPage:()=>1,FPDF_GetPageWidthF:()=>18,FPDF_GetPageHeightF:()=>24,FPDFBitmap_Create:(w,h)=>{width=w;height=h;return 1;},
    FPDFBitmap_FillRect:()=>heap.fill(255,8192,8192+width*height*4),FPDF_RenderPageBitmap:()=>{for(let y=0;y<30;y++)heap.fill(0,8192+y*(width+1)*4,8192+y*(width+1)*4+4);},
    FPDFBitmap_GetBuffer:()=>8192,FPDFBitmap_GetStride:()=>width*4,FPDFBitmap_Destroy(){},FPDF_ClosePage(){},FPDF_CloseDocument(){}};
}
