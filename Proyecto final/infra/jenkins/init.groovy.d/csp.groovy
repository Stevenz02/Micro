// Permite estilos en línea en los reportes HTML publicados con publishHTML (cucumber.html).
// Jenkins por defecto los bloquea y el reporte se vería sin formato. Solo uso académico/local.
System.setProperty("hudson.model.DirectoryBrowserSupport.CSP",
    "sandbox allow-scripts allow-same-origin; default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
