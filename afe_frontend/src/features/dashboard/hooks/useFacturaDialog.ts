/**
 * Custom hook for managing factura dialog state
 */

import { useState, useCallback } from 'react';
import type { Factura, FacturaFormData, DialogMode } from '../types';
import { extractDateForInput, getTodayDate } from '../utils';

interface UseFacturaDialogReturn {
  openDialog: boolean;
  dialogMode: DialogMode;
  selectedFactura: Factura | null;
  formData: FacturaFormData;
  setFormData: React.Dispatch<React.SetStateAction<FacturaFormData>>;
  openDialogWith: (mode: DialogMode, factura?: Factura) => void;
  closeDialog: () => void;
}

const getInitialFormData = (): FacturaFormData => ({
  numero_factura: '',
  nit_emisor: '',
  nombre_emisor: '',
  monto_total: '',
  fecha_emision: getTodayDate(),
  fecha_vencimiento: '',
  observaciones: '',
});

const getFormDataFromFactura = (factura: Factura): FacturaFormData => ({
  numero_factura: factura.numero_factura || '',
  nit_emisor: factura.nit_emisor || '',
  nombre_emisor: factura.nombre_emisor || '',
  monto_total: factura.monto_total ? factura.monto_total.toString() : '',
  fecha_emision: extractDateForInput(factura.fecha_emision),
  fecha_vencimiento: extractDateForInput(factura.fecha_vencimiento),
  observaciones: factura.observaciones || '',
});

export const useFacturaDialog = (): UseFacturaDialogReturn => {
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogMode, setDialogMode] = useState<DialogMode>('view');
  const [selectedFactura, setSelectedFactura] = useState<Factura | null>(null);
  const [formData, setFormData] = useState<FacturaFormData>(getInitialFormData());

  const openDialogWith = useCallback((mode: DialogMode, factura?: Factura) => {
    setDialogMode(mode);

    if (factura) {
      setSelectedFactura(factura);
      setFormData(getFormDataFromFactura(factura));
    } else {
      setSelectedFactura(null);
      setFormData(getInitialFormData());
    }

    setOpenDialog(true);
  }, []);

  const closeDialog = useCallback(() => {
    setOpenDialog(false);
    setSelectedFactura(null);
  }, []);

  return {
    openDialog,
    dialogMode,
    selectedFactura,
    formData,
    setFormData,
    openDialogWith,
    closeDialog,
  };
};
