SELECT pg_catalog.setval(
  'public.performances_id_seq',
  COALESCE((SELECT MAX(id) FROM public.performances), 1),
  true
);

SELECT pg_catalog.setval(
  'public.venues_id_seq',
  COALESCE((SELECT MAX(id) FROM public.venues), 1),
  true
);

CREATE INDEX IF NOT EXISTS idx_performances_genre ON public.performances(genre);
CREATE INDEX IF NOT EXISTS idx_performances_status ON public.performances(status);
CREATE INDEX IF NOT EXISTS idx_performances_start_date ON public.performances(start_date);
CREATE INDEX IF NOT EXISTS idx_venues_province ON public.venues(province);
