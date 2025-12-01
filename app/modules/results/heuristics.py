"""
heuristics.py
--------------------------------------------------------------------
Heuristiksammlung zur Klassifikation von Webtechnologien
--------------------------------------------------------------------

Dieses Modul enthält definierte Listen bekannter Technologien, die
innerhalb der Analyse- und Bewertungskomponenten eingesetzt werden,
um Webseiten anhand erkennbarer technischer Merkmale einzuordnen.

Die Klassifikation erfolgt typischerweise über die in der Analyse
extrahierten Technologiebezeichnungen (z. B. aus Wappalyzer), die anschließend mit den hier definierten Listen
abgeglichen werden. Auf diese Weise lassen sich u. a. folgende
Aspekte bestimmen:

--------------------------------------------------------------------
• statisch generierte Seiten (Static Site Generators)
• statische Hosting-Plattformen
• dynamische Webframeworks
• Laufzeitumgebungen verbreiteter CMS-Systeme
• Virtualisierungs- und Isolationsumgebungen (Container, VMs etc.)
--------------------------------------------------------------------

Diese Listen unterstützen verschiedene Bewertungskomponenten, unter
anderem die Analyse der technischen Architektur (z. B.
score_static_technologies) oder der infrastrukturellen Isolation
(z. B. score_global_isolation).

Die Einträge wurden bewusst breit zusammengestellt, um eine möglichst
hohe Erkennungswahrscheinlichkeit in realen Webumgebungen zu erzielen.
Die vorliegenden Listen bleiben inhaltlich unverändert.
--------------------------------------------------------------------
"""


# ------------------------------------------------------------------
# Static Site Generators
# ------------------------------------------------------------------
# Technologien, die auf das Erzeugen rein statischer Webangebote
# spezialisiert sind. Erkennt ein Analysemodul eine dieser
# Technologien, wird dies als starker Hinweis auf einen
# statischen Seitenaufbau gewertet.

STATIC_SITE_GENERATORS = [
    "ablog", "ace", "acrylamid", "adduce", "akashacms", "akashic", "antwar", "appernetic",
    "assemble", "astro", "aurora", "automad", "awestruct", "axiom", "aym cms", "baker", "balloon",
    "bam", "bashblog", "basildon", "bazinga", "beetle", "benjen", "bitbucket cloud", "blacksmith",
    "blag", "blatter", "blazeblogger", "bliper", "blode", "blogc", "blogc++", "blogen", "bloggrify",
    "blogit", "blogofile", "blogpy", "blosxom", "blug", "bonsai", "bramble mvc", "bread",
    "bricolage cms", "bridgetown", "broccoli taco", "brochure", "bryar", "bunto", "buster",
    "cabin", "cactus", "caixw-blogit", "calepin", "capro", "carew", "catsup", "cecil", "chili",
    "chisel", "chronicle", "cipherpress", "cl-blog-generator", "cl-yag", "cloud cannon", "cmints",
    "cobalt.rs", "codex", "coisas", "coleslaw", "composer", "contentful", "cory", "create static web",
    "cub", "curvenote", "cyrax", "cytoplasm", "dapper", "daux.io", "deplate", "desi", "django-medusa",
    "django-staticgen", "djangothis", "docknot", "docpad", "docta", "docusaurus", "drapache",
    "drfrederson", "dropbox-blog", "dropplets", "droppress", "drupan", "dssg", "dsw", "dwttool",
    "dynamicmatic", "easystatic", "ecstatic", "electro", "eleventy", "embellih", "enfield", "engineer",
    "equiprose", "fairytale", "fantasticwindmill", "fblog", "firmant", "fjord", "flamel",
    "fledermaus", "flim", "floyd", "fmpp", "ford.py", "frank", "franklin", "frog", "frozen-flask",
    "funnel", "garoozis", "gatsby", "gen", "generic static site generator", "genesis", "gerablog",
    "gettheshitdone", "ghost-render", "github pages", "gitlab pages", "glyph", "go-static!",
    "goldbarg", "gollum-site", "gor", "gostatic", "grain", "grav", "grav administration panel", "graze",
    "grender", "griffin", "grow", "growl", "grunt-generator", "gsl", "guetzli", "gulp-ssg", "gustav",
    "habit", "haggis", "hakyll", "halwa", "hammer", "hanayo", "handcrank", "handle", "handroll",
    "happyplan", "harmonic", "haroldjs", "haroopress", "harp", "hastie", "haunt", "heckle",
    "helpful site", "hepek", "hexo", "hid", "high voltage", "hsc", "htmd", "hublo", "hubpress", "hugo",
    "hyde", "hyde (chicken)", "hydrastic", "igapyon", "igor", "ikiwiki", "ink", "ipsum genera", "jagss",
    "jbake", "jedie", "jekxll", "jekyde", "jekyll", "jekyll admin", "jekyll now", "jekytrum",
    "jem-press", "jen", "jigsaw", "jinjet", "jkl", "jott", "journo", "jr", "jssg", "jstatico",
    "kalastatic", "kel", "kerouac", "kirby", "kkr", "korma", "kulfon", "lambda pad", "lannister",
    "lanyon", "latemp", "lava", "laze", "lazyblorg", "leeflets", "lektor", "lenscap", "leo",
    "letterpress", "lettersmith", "liara", "lightning", "liquidluck", "log4brains", "logya", "luapress",
    "lume", "machined", "madoko", "magneto", "makeblog", "makefly", "makesite.py", "markbox",
    "markdoc", "markdown-styles", "markx", "massimo", "maven site plugin", "mdwiki", "mecha",
    "meinhof", "metalsmith", "miblo", "middleman", "minimal", "minoriwiki", "misakai baker", "misaki",
    "mkdocs", "mksite", "mkws", "monkeyman", "mulder", "muleify", "mynt", "nanoblogger", "nanoc",
    "nanogen", "nestacms", "netlify drop", "neverland", "newcomen", "nib", "nibbleblog",
    "nico", "nikola", "node-blog", "node-qssg", "nodeache", "noflo-jekyll", "noter",
    "o-blog", "oak", "obelisk", "ocam", "octopress", "onessg", "operator-dd3", "opoopress", "orca",
    "orchid", "page", "pagegen", "pagen", "pancake.io", "pansite", "papery", "pelican", "perun",
    "petrify", "phenomic", "phileas", "phlyblog", "phpetite", "piecrust", "pilcrow", "pith", "pmblog",
    "poet", "pointless", "polo", "poole", "pop", "portable-php", "powersite", "pretzel", "prismic",
    "propeller", "prose", "prosopopee", "publii", "pulse cms", "punch", "pyblosxom", "pyblue", "pyll",
    "qgoda", "quietly confident", "quill", "rakeweb", "rant", "rassmalog", "rawk", "reacat",
    "react-static", "react-static-site", "reactivate", "read the docs (rtd)", "really static", "refrain",
    "regenerate", "reptar", "riji", "rizzo", "romulus", "roots", "rosid", "rstblog", "rubyfrontier",
    "ruhoh", "s2gen", "saait", "sblg", "scroll", "sculpin", "second crack", "serif", "serious-chicken",
    "serve", "sessg", "sg", "sg.py", "sgg", "shelob", "shinobi", "shire", "shonku", "silex", "simiki",
    "simple", "simple-static", "simsalabash", "site builder", "site builder console", "site44",
    "sitegen (dart)", "sitegen (moonscript)", "sitio", "smallest blogger", "snowshoe", "soapbox",
    "socrates", "sortastatic", "speechhub", "spelt", "spg", "sphinx", "spike", "spina", "spress",
    "squid", "squido", "squirrel", "stacey", "stacktic", "stad", "stagen", "stapy", "stasis",
    "stasis.clj", "statamic", "stati", "static", "static site boilerplate", "static website starter kit",
    "static-io", "static-weber", "static2000", "staticjinja", "staticmatic", "staticmatic2",
    "staticpress", "staticpy", "staticsite", "staticsmoothie", "staticvolt", "statik", "statiq",
    "statix", "statocles", "strangecase", "stratic", "striker", "surge", "susi", "swg", "swsg",
    "szyslak", "tacot", "tags", "tagy", "tahchee", "tapestry", "tarbell", "tclog", "tclssg", "techy",
    "templer", "thot", "tinkerer", "toto", "tribo", "trofaf", "ultra simple site maker", "urubu",
    "utterson", "uzu", "vee", "vegetables", "vimwiki", "voldemort", "volt", "voodoopad", "vuepress",
    "wadoo", "wallflower", "wanna", "weaver", "webby", "webgen", "webhook", "websleydale", "wheat",
    "wikismith", "wintersmith", "wok", "woods", "wordsister", "wp2static", "wpwmm4", "wyam", "yana",
    "yassg", "yellow", "yggdrasil", "yozuch", "yst", "zas", "zenweb", "zine", "zodiac", "zola",
    "zucchini"
]

# ------------------------------------------------------------------
# Static Hosting Platforms
# ------------------------------------------------------------------
# Dienste, die typischerweise rein statische Inhalte ausliefern.
# Werden sie erkannt, kann dies ein Hinweis darauf sein, dass
# die zugrundeliegende Seite als statisches Projekt umgesetzt ist.

STATIC_HOST_PLATFORMS = [
    "aws s3", "azure static web apps", "cloudflare pages", "gitlab pages",
    "kinsta static site hosting", "netlify", "pgs", "surge", "vercel"
]

# ------------------------------------------------------------------
# Dynamic Frameworks
# ------------------------------------------------------------------
# Technologien, die auf serverseitige oder dynamische Erzeugung
# von Webseiten hindeuten. Ein Treffer in dieser Liste spricht
# für eine dynamische Architektur (z. B. Python, JS, PHP, Java).

DYNAMIC_FRAMEWORKS = [
    "asp.net", "bfc", "csla", "monorail", "cppcms", "drogon", "poco", "wt",
    "coldbox", "phoenix", "snap", "yesod", "apache click", "apache ofbiz", "apache shale",
    "apache sling", "apache struts", "apache tapestry", "apache wicket", "appfuse", "mojarra",
    "eclipse rap", "grails", "google web toolkit", "jboss seam", "jwt", "netty", "openlaszlo",
    "oracle adf", "play", "spring", "stripes", "vaadin", "wavemaker", "webobjects",
    "express.js", "fastify", "meteor", "nestjs", "nuxt.js", "remix", "sails.js",
    "sveltekit", "catalyst", "dancer", "maypole", "mojolicious", "cakephp", "codeigniter",
    "fat-free", "fuelphp", "gyroscope", "jamroom", "kajona", "laminas", "laravel", "li3",
    "phalcon", "pop php", "prado", "silverstripe", "smart.framework", "symfony", "yii",
    "bluebream", "cherrypy", "cubicweb", "django", "fastapi", "flask", "grok", "gunicorn",
    "pylons", "pyramid", "tornado", "turbogears", "web2py", "zope 2", "padrino",
    "ruby on rails", "sinatra", "lift", "play (scala)", "scalatra", "aida/web", "oracle apex",
    "flex", "grails (groovy)", "morfik", "opa", "openacs", "seaside"
]

# ------------------------------------------------------------------
# CMS Runtimes
# ------------------------------------------------------------------
# Verbreitete Content-Management-Systeme, die serverseitig
# dynamische Inhalte erzeugen. Ein Treffer bedeutet typischerweise,
# dass Inhalte nicht statisch vorkompiliert werden.

CMS_RUNTIME = [
    "WordPress", "Drupal"
]

# ------------------------------------------------------------------
# Isolation / Virtualization Technologies
# ------------------------------------------------------------------
# Technologien, die auf den Einsatz von Containern, VMs oder
# anderen Formen isolierter Ausführungsumgebungen hinweisen.
# Treffer dienen als starke Evidenz für professionelle,
# containerisierte oder virtualisierte Deployments.

ISO_STRONG = [
    "apptainer", "borg", "containerd", "denali", "diego", "docker",
    "docker-compose", "docker-swarm", "dockercompose", "dockerd", "dockerswarm",
    "esxi", "etcd", "freebsd-jail", "k8s", "kubernetes", "kvm", "libvirtd",
    "lxc", "lxcfs", "lxd", "marathon", "mesos", "openvz", "podman",
    "qemu-kvm", "rkt", "rocket", "runc", "singularity", "solaris-zone",
    "swarm", "virtuozzo", "vlx", "vmtoolsd", "vmware", "vmware-guestd",
    "vzctl", "vzlist", "xen", "xenserver", "xtratum", "zoneadmd"
]