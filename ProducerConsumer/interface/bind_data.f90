module bind_data
    use iso_c_binding
    
    implicit none
    
    type, bind(c) :: fKeyMessage
      integer(c_int) :: actionType
      character(kind=c_char, len=32) :: key
      integer(c_int) :: npatches
      integer(c_int) :: myrank
      integer(c_size_t) :: datetime
      integer(c_size_t) :: ilon_start, jlat_start, lev, lonlen, latlen, levlen, totlonlen, totlatlen
      real(c_float) :: longitudeOfFirstGridPoint, longitudeOfLastGridPoint, latitudeOfFirstGridPoint, latitudeOfLastGridPoint
    end type

end module