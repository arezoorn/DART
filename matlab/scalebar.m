   function ax=scalebar(xmin,ymin,wid,height,zmin,zmax)
%
%  h = scalebar(xmin,ymin,wid,height,[zmin],[zmax])
%
%  Makes a scale of the size and positions specified. The values 
%  zmin, zmax are annotated at the left(bottom) and right(top) ends 
%  of the scalebar for reference.
%
%  If zmin,zmax are not supplied, the UserData attribute of the
%  current axis is used.
%
% returns a handle ...
%
%  scalebar ONLY uses the first 64 colors in a colormap ...

% Data Assimilation Research Testbed -- DART
% Copyright 2004, Data Assimilation Initiative, University Corporation for Atmospheric Research
% Licensed under the GPL -- www.gpl.org/licenses/gpl.html

   if nargin <= 4,
      zmin = get(gca,'UserData');
      zmin = get(gca,'Clim');
      if length(zmin) == 0,
	 disp('WARNING: unknown data bounds, using [1,64]')
         zmax =  1;
         zmin = 64;
      else
         zmax = zmin(2);
         zmin = zmin(1);
      end
   end

   if strcmp(get(gcf,'NextPlot'),'replace'),
     set(gcf,'NextPlot','add')
   end

   ax = axes('position',[ xmin ymin wid height ]);
   frog = [1:64];
   m = (zmax-zmin)/(64-1);
   b = zmin - m;
   x_axis =  frog*m + b;

   if (wid > height)
      image(x_axis,[1 2],frog)
      axis([ zmin zmax 1 2 ])
      set(ax,'YTickLabel',[])
   else
      image([1 2],x_axis,frog'); set(ax,'YDir','normal');
      axis([ 1 2 zmin zmax ]);
      set(ax,'XTickLabel',[]);
      set(ax,'YAxisLocation','right')
   end
